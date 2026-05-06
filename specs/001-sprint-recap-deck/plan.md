# Implementation Plan: Sprint Recap Deck Generator

**Branch**: `001-sprint-recap-deck` | **Date**: 2026-05-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-sprint-recap-deck/spec.md`

## Summary

Produce a small Python desktop program that, when launched from a working folder
containing a pptx template, talks to YouTrack to retrieve the most recently
closed (or user-picked) sprint, then writes a new pptx alongside the template
with date tokens substituted and the agenda slide populated by Finished/Open
issue lists. First-time setup prompts (URL, project, board, optional sprint)
are console-based when stdin is a TTY and `tkinter`-based otherwise; non-token
settings persist in a per-folder JSON file; the access token is read from the
`YOUTRACK_TOKEN` environment variable each run. Pptx editing uses `python-pptx`
(the only third-party dependency); HTTP, JSON, logging, and dialogs use the
Python standard library.

## Technical Context

**Language/Version**: Python 3.11+ (per constitution Principle V).
**Primary Dependencies**: `python-pptx` (read/write of `.pptx` — a zipped XML
format whose round-trip is materially harder to hand-roll; broadly recognized
on PyPI). All other functionality (HTTP via `urllib.request`, JSON, logging,
dialogs via `tkinter`, TTY detection via `sys.stdin.isatty()`) uses the Python
standard library.
**Storage**: Per-folder settings file `sprint-recap.json` (plain JSON; written
by the program; never contains the token). Per-run log file
`<output-stem>.log` in the same folder.
**Testing**: `pytest` for unit tests on the deterministic pure-function pieces
(date formatting, sort/classification, subtask collapse, filename sanitization,
token replacement against a small fixture pptx). End-to-end runs are verified
manually by the user at iteration boundaries per constitution Principle I; the
agent does not run or verify product behavior on the user's behalf.
**Target Platform**: Desktop OSes that ship a current Python (Windows 10/11
primary — that is where the double-click contract matters most; also macOS and
Linux). No platform-specific calls.
**Project Type**: Single-project Python desktop application launched by
double-clicking a top-level entry script (`sprint_recap.py`).
**Performance Goals**: End-to-end run under 1 minute on the routine monthly
case (SC-001); typical sprint size 10–100 issues. No latency budgets beyond
"feels instant after the YouTrack fetch returns."
**Constraints**:
- Token (`YOUTRACK_TOKEN`) MUST never be written to settings, logs, or output.
- The program MUST NOT write outside the working folder unless the user
  explicitly redirects it at a prompt (constitution III, FR-013).
- The original template file MUST be byte-for-byte unchanged (FR-003, SC-006).
- Re-runs for the same sprint MUST produce the same output filename so the
  overwrite prompt fires (FR-003, FR-004).
- Output is exactly one agenda slide; visual fit delegated to the template's
  text-frame autofit (FR-010).
**Scale/Scope**: Single user, monthly cadence, ~10–100 issues per sprint, one
working folder per project. Not concurrent, not networked beyond the YouTrack
REST call.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluating against `pptx-helper Constitution v1.0.0`:

- **I. Incremental Delivery with Frequent Feedback (NON-NEGOTIABLE)** — PASS.
  The downstream `tasks.md` will use the Iteration Ladder structure; each
  iteration delivers a runnable vertical slice (e.g., I1 produces a deck with
  hardcoded data; I2 reads YouTrack; I3 adds first-time setup; I4 adds sprint
  picker; I5 adds issue-type filter & subtask collapse). The agent stops at
  iteration boundaries and hands off to the user.
- **II. Minimal Dependency Footprint** — PASS. Single third-party dependency:
  `python-pptx`. Justification: pptx is a zipped Office Open XML container
  whose correct round-trip (preserving slide layouts, masters, autofit, and
  the rest of the template's structure) would be materially harder and riskier
  to hand-roll than to delegate to the canonical, broadly-adopted library
  (`python-pptx` on PyPI, widely used across mainstream Python). HTTP to
  YouTrack is intentionally `urllib.request` — `requests` would be a
  convenience wrapper that fails Principle II's second bar. No GUI framework
  beyond stdlib `tkinter`.
- **III. Folder-as-Context Execution** — PASS. The entry script lives in the
  working folder, treats `Path(__file__).parent` (or `os.getcwd()` when
  launched as a script from a folder) as the working folder, finds the
  template inside it, and writes outputs back into it. No global config, no
  hidden working directory, no install step required for the default flow.
- **IV. Conversational Fallback for Ambiguity** — PASS. Every gap in inferable
  input is a prompt: missing/multiple templates, multiple boards, multiple
  sprints, overwrite confirmation, missing token (with explicit guidance to
  set `YOUTRACK_TOKEN`). Prompt mode auto-detected once at startup
  (`sys.stdin.isatty()`) and held constant for the run; mode is logged.
- **V. Standard Python Packaging & Portability** — PASS. `requirements.txt`
  with one pinned dependency; `venv`-based setup documented in `quickstart.md`
  and `README.md`; entry point is `sprint_recap.py` at the project root,
  associable with the system Python on Windows for double-click; Python 3.11+
  language features only.

No violations. Complexity Tracking section remains empty.

**Post-Phase-1 re-check (re-evaluated after research.md, data-model.md,
contracts/, and quickstart.md were written)**: still PASS on all five
principles. The Phase 1 design introduced no new dependencies (only
`python-pptx`), no global state, no install step, and surfaces every
ambiguity as a prompt. The pptx-token paragraph-coalescing trade-off in
`contracts/template-tokens.md` is explicit, scoped, and within the
spec's intent (FR-009 / FR-010), so it does not require an entry in
Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-sprint-recap-deck/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (this run)
├── data-model.md        # Phase 1 output (this run)
├── quickstart.md        # Phase 1 output (this run)
├── contracts/           # Phase 1 output (this run)
│   ├── settings-file.md
│   ├── template-tokens.md
│   ├── log-file.md
│   ├── output-filename.md
│   └── youtrack-api.md
├── checklists/
│   └── requirements.md  # (already present from /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
sprint_recap.py          # Double-clickable entry point; thin shim that
                         # invokes sprint_recap.app:main() under
                         # `if __name__ == "__main__":`
sprint_recap/
├── __init__.py
├── app.py               # main() — orchestrates one run end-to-end
├── config.py            # Load/save sprint-recap.json; token from env
├── youtrack.py          # urllib-based REST client (sprints, issues)
├── classify.py          # Finished/Open split, subtask collapse, sort
├── deck.py              # python-pptx token substitution
├── prompts.py           # Console + tkinter prompt facade selected once
├── logging_setup.py     # Per-run dual-sink logger (file + console)
└── naming.py            # Filename pattern + filesystem-safe sanitization

tests/
├── unit/
│   ├── test_classify.py
│   ├── test_naming.py
│   ├── test_dates.py
│   └── test_deck_tokens.py     # uses a tiny fixture pptx
└── fixtures/
    └── template.pptx           # minimal template carrying the five tokens

requirements.txt         # single dependency line: python-pptx==<pin>
README.md                # human-readable setup + run instructions
.gitignore               # venv/, *.log, sprint-recap.json (per-folder, but
                         # repo root is not a "working folder" itself)
```

**Structure Decision**: Single-project Python desktop application. The
top-level `sprint_recap.py` is the double-click entry point and is a thin
shim only; the actual code lives in the `sprint_recap/` package so each
module stays small and independently testable. Tests sit in a parallel
`tests/` tree mirroring the package. No separate CLI/lib split — there is
one program with one entry point.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none)    | (none)     | (none)                              |
