"""Output filename pattern and filesystem-safe sanitization.

Per FR-003, research §R4, contracts/output-filename.md:
    <template-stem>_<sprint-name>_<sprint-end-YYYY-MM-DD>.pptx
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

_ALLOWED = re.compile(r"[^A-Za-z0-9._-]")
_RUNS = re.compile(r"_+")


def _sanitize(name: str) -> str:
    s = _ALLOWED.sub("_", name)
    s = _RUNS.sub("_", s)
    return s.strip("_")


def output_filename(
    template_stem: str,
    sprint_name: str,
    sprint_end_date: date,
    idreadable_fallback: str,
) -> str:
    sanitized = _sanitize(sprint_name)
    if not sanitized:
        sanitized = idreadable_fallback
    iso = sprint_end_date.strftime("%Y-%m-%d")
    return f"{template_stem}_{sanitized}_{iso}.pptx"


def output_paths(
    working_folder: Path,
    template_path: Path,
    sprint_name: str,
    sprint_end: date,
    idreadable_fallback: str,
) -> tuple[Path, Path]:
    fname = output_filename(
        template_path.stem, sprint_name, sprint_end, idreadable_fallback
    )
    pptx = working_folder / fname
    log = pptx.with_suffix(".log")
    return pptx, log
