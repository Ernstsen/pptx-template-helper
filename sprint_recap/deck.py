"""Long-form English date rendering and pptx token substitution.

Date rendering (research §R5, FR-009):
    f"{day} {month_name} {year}" with hard-coded English month names.

Token substitution (contracts/template-tokens.md):
    - Date tokens replaced in-place at the paragraph level (surrounding
      text preserved). Paragraph runs are coalesced into one run carrying
      the existing first run's formatting; the documented trade-off is
      that inline (mid-paragraph) run formatting is lost. Paragraph-level
      formatting and the text frame's body properties (`bodyPr`,
      including `normAutofit`) are preserved.
    - Agenda tokens replace the entire text frame: the frame is cleared,
      then one paragraph per issue title is written in given order. The
      first written paragraph reuses the original first run's formatting
      where present so the user's bullet style carries over.
    - Required tokens missing → clear error naming the missing token.
    - {{AGENDA_FINISHED}} or {{AGENDA_OPEN}} appearing more than once →
      explicit error.
"""

from __future__ import annotations

import copy
from datetime import date
from pathlib import Path
from typing import Iterable, Sequence

from pptx import Presentation
from pptx.text.text import _Paragraph, _Run, TextFrame  # noqa: F401  (typing)

from sprint_recap.models import AgendaPlan, Sprint, SprintIssue


_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

DATE_TOKENS = ("{{SPRINT_START}}", "{{SPRINT_END}}", "{{RECAP_DATE}}")
AGENDA_FINISHED_TOKEN = "{{AGENDA_FINISHED}}"
AGENDA_OPEN_TOKEN = "{{AGENDA_OPEN}}"


def format_long_date(d: date) -> str:
    return f"{int(d.day)} {_MONTHS[d.month - 1]} {d.year}"


def _iter_text_frames(prs) -> Iterable:
    """Yield every text frame in slide bodies, including descendants of
    group shapes. Excludes masters, layouts, speaker notes, and chart
    text per template-tokens contract §"Where each token may live"."""
    for slide in prs.slides:
        yield from _iter_shapes_text_frames(slide.shapes)


def _iter_shapes_text_frames(shapes) -> Iterable:
    for shape in shapes:
        if shape.shape_type == 6:  # MSO_SHAPE_TYPE.GROUP
            yield from _iter_shapes_text_frames(shape.shapes)
            continue
        if shape.has_text_frame:
            yield shape.text_frame


def _replace_in_paragraph(paragraph: _Paragraph, old: str, new: str) -> bool:
    """Replace `old` with `new` inside a paragraph, coalescing runs into the
    first run. Returns True if a replacement was made.

    The paragraph's formatting (font, bullet style) is preserved by reusing
    the first run's `rPr`. Subsequent runs are removed so the paragraph
    holds a single run with the new text.
    """
    full_text = paragraph.text
    if old not in full_text:
        return False
    new_text = full_text.replace(old, new)

    runs = paragraph.runs
    if not runs:
        # Empty paragraph; just set text.
        paragraph.text = new_text
        return True

    # Keep first run's text+formatting, drop the rest.
    first = runs[0]
    first.text = new_text
    # Remove subsequent <a:r> / <a:br> elements while keeping <a:pPr>.
    p_elem = paragraph._p
    keep = first._r
    for child in list(p_elem):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "pPr":
            continue
        if child is keep:
            continue
        p_elem.remove(child)
    return True


def _count_token_in_text_frames(text_frames, token: str) -> int:
    n = 0
    for tf in text_frames:
        for para in tf.paragraphs:
            if token in para.text:
                n += para.text.count(token)
    return n


def _clear_text_frame(text_frame) -> _Run | None:
    """Clear all paragraphs from a text frame, preserving the first run's
    rPr template (so the caller can clone its formatting onto subsequent
    paragraphs). Returns the first run before clearing, or None if the
    frame had no runs.

    `python-pptx` does not expose a direct paragraph-delete API, so we
    drop child <a:p> elements from the txBody and let
    `text_frame.text = ""` recreate a single empty paragraph.
    """
    template_run = None
    if text_frame.paragraphs:
        first_runs = text_frame.paragraphs[0].runs
        if first_runs:
            template_run = first_runs[0]

    # Snapshot the first run's rPr (formatting) before we wipe the frame.
    rpr_xml = None
    if template_run is not None and template_run._r.find(
        "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr"
    ) is not None:
        rpr_xml = copy.deepcopy(
            template_run._r.find(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr"
            )
        )

    text_frame.clear()  # leaves one empty paragraph
    return rpr_xml  # type: ignore[return-value]


def _write_agenda(text_frame, issues: Sequence[SprintIssue]) -> None:
    rpr_xml = _clear_text_frame(text_frame)

    if not issues:
        # Leave the frame empty (one empty paragraph from clear()).
        return

    # First paragraph reuses the cleared frame's existing paragraph object.
    first_para = text_frame.paragraphs[0]
    first_para.text = issues[0].title
    if rpr_xml is not None and first_para.runs:
        # Clone the captured rPr onto the new run.
        first_run_elem = first_para.runs[0]._r
        existing_rpr = first_run_elem.find(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr"
        )
        if existing_rpr is not None:
            first_run_elem.remove(existing_rpr)
        first_run_elem.insert(0, copy.deepcopy(rpr_xml))

    for issue in issues[1:]:
        para = text_frame.add_paragraph()
        para.text = issue.title
        if rpr_xml is not None and para.runs:
            run_elem = para.runs[0]._r
            existing_rpr = run_elem.find(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr"
            )
            if existing_rpr is not None:
                run_elem.remove(existing_rpr)
            run_elem.insert(0, copy.deepcopy(rpr_xml))


def render_deck(
    template_path: Path,
    output_path: Path,
    sprint: Sprint,
    agenda_plan: AgendaPlan,
) -> None:
    prs = Presentation(str(template_path))

    text_frames = list(_iter_text_frames(prs))

    # --- Validate token presence and cardinality before any edits. ---
    missing: list[str] = []

    def _present(token: str) -> int:
        return _count_token_in_text_frames(text_frames, token)

    sprint_start_n = _present("{{SPRINT_START}}")
    sprint_end_n = _present("{{SPRINT_END}}")
    finished_n = _present(AGENDA_FINISHED_TOKEN)
    open_n = _present(AGENDA_OPEN_TOKEN)

    if sprint_start_n == 0:
        missing.append("{{SPRINT_START}}")
    if sprint_end_n == 0:
        missing.append("{{SPRINT_END}}")
    if finished_n == 0:
        missing.append(AGENDA_FINISHED_TOKEN)
    if open_n == 0:
        missing.append(AGENDA_OPEN_TOKEN)
    if missing:
        raise ValueError(
            "Required template tokens missing: " + ", ".join(missing)
        )

    if finished_n > 1:
        raise ValueError(
            f"Token {AGENDA_FINISHED_TOKEN} appears more than once in the "
            "template; cannot infer which occurrence wins."
        )
    if open_n > 1:
        raise ValueError(
            f"Token {AGENDA_OPEN_TOKEN} appears more than once in the "
            "template; cannot infer which occurrence wins."
        )

    # --- Date substitution (paragraph-level, in place). ---
    start_str = format_long_date(sprint.start)
    end_str = format_long_date(sprint.end)
    recap_str = end_str  # FR-009: recap-meeting date == sprint end.

    for tf in text_frames:
        for para in tf.paragraphs:
            text = para.text
            if (
                "{{SPRINT_START}}" in text
                or "{{SPRINT_END}}" in text
                or "{{RECAP_DATE}}" in text
            ):
                # Apply all three in one coalesce; order matters only
                # because the helper rewrites the run on each call.
                if "{{SPRINT_START}}" in para.text:
                    _replace_in_paragraph(para, "{{SPRINT_START}}", start_str)
                if "{{SPRINT_END}}" in para.text:
                    _replace_in_paragraph(para, "{{SPRINT_END}}", end_str)
                if "{{RECAP_DATE}}" in para.text:
                    _replace_in_paragraph(para, "{{RECAP_DATE}}", recap_str)

    # --- Agenda substitution (clear + write per issue). ---
    for tf in text_frames:
        # Recompute presence inside this loop because earlier date-token
        # replacements may have rewritten the paragraph text. Agenda
        # tokens are expected to be the sole content of their text frame
        # per the contract, so the lookup stays exact.
        joined = "\n".join(p.text for p in tf.paragraphs)
        if AGENDA_FINISHED_TOKEN in joined:
            _write_agenda(tf, agenda_plan.finished)
        elif AGENDA_OPEN_TOKEN in joined:
            _write_agenda(tf, agenda_plan.open)

    prs.save(str(output_path))
