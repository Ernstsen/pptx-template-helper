"""Filename sanitization and pattern (FR-003, research §R4, contracts/output-filename.md)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from sprint_recap.naming import output_filename, output_paths


SPRINT_END = date(2026, 5, 5)
TEMPLATE_STEM = "Recap-Template"
ID_FALLBACK = "121-318"


@pytest.mark.parametrize(
    "sprint_name, expected_sprint_segment",
    [
        ("Sprint 42", "Sprint_42"),
        ("Q2/2026 — Recap", "Q2_2026_Recap"),
        ("R&D — week 18", "R_D_week_18"),
        ("🚀 launch sprint", "launch_sprint"),
    ],
)
def test_output_filename_sanitization(sprint_name: str, expected_sprint_segment: str) -> None:
    fname = output_filename(TEMPLATE_STEM, sprint_name, SPRINT_END, ID_FALLBACK)
    assert fname == f"{TEMPLATE_STEM}_{expected_sprint_segment}_2026-05-05.pptx"


def test_output_filename_falls_back_to_idreadable_when_empty_after_sanitize() -> None:
    # Pure non-ASCII punctuation collapses to empty → fallback.
    fname = output_filename(TEMPLATE_STEM, "🎉🎉🎉", SPRINT_END, ID_FALLBACK)
    assert fname == f"{TEMPLATE_STEM}_{ID_FALLBACK}_2026-05-05.pptx"


def test_output_filename_collapses_underscore_runs() -> None:
    # Multiple spaces / punctuation in a row should collapse to a single _.
    assert (
        output_filename(TEMPLATE_STEM, "Sprint   42!!!", SPRINT_END, ID_FALLBACK)
        == f"{TEMPLATE_STEM}_Sprint_42_2026-05-05.pptx"
    )


def test_output_filename_strips_leading_trailing_underscore() -> None:
    assert (
        output_filename(TEMPLATE_STEM, "  weird  ", SPRINT_END, ID_FALLBACK)
        == f"{TEMPLATE_STEM}_weird_2026-05-05.pptx"
    )


def test_output_filename_preserves_case() -> None:
    assert "ABCxyz" in output_filename(TEMPLATE_STEM, "ABCxyz", SPRINT_END, ID_FALLBACK)


def test_output_filename_zero_pads_iso_date() -> None:
    fname = output_filename(TEMPLATE_STEM, "Sprint 42", date(2026, 1, 9), ID_FALLBACK)
    assert fname.endswith("_2026-01-09.pptx")


def test_output_paths_returns_pptx_and_log_in_working_folder(tmp_path: Path) -> None:
    template = tmp_path / "Recap-Template.pptx"
    template.write_bytes(b"")
    output_pptx, log = output_paths(
        working_folder=tmp_path,
        template_path=template,
        sprint_name="Sprint 42",
        sprint_end=SPRINT_END,
        idreadable_fallback=ID_FALLBACK,
    )
    assert output_pptx == tmp_path / "Recap-Template_Sprint_42_2026-05-05.pptx"
    assert log == tmp_path / "Recap-Template_Sprint_42_2026-05-05.log"


def test_output_filename_deterministic_across_runs() -> None:
    a = output_filename(TEMPLATE_STEM, "Sprint 42", SPRINT_END, ID_FALLBACK)
    b = output_filename(TEMPLATE_STEM, "Sprint 42", SPRINT_END, ID_FALLBACK)
    assert a == b
