---

description: "Task list for Sprint Recap Deck Generator (feature 001-sprint-recap-deck)"
---

# Tasks: Sprint Recap Deck Generator

**Input**: Design documents from `/specs/001-sprint-recap-deck/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (settings-file.md, template-tokens.md, log-file.md, output-filename.md, youtrack-api.md), quickstart.md

**Tests**: Tests are included. Plan.md §R10 enumerates the unit-test scope (date rendering, classification + sort + subtask collapse, filename sanitization, and a token-substitution smoke test against a fixture pptx). Tests are written before the corresponding implementation within each iteration.

**Organization**: Tasks form an ordered **Iteration Ladder** per the project's `tasks-template.md`. Each iteration delivers one user story end-to-end. Iteration 1 absorbs all bootstrap (project layout, dependencies, entry point, logging, deck rendering) needed to produce a working deck. Iteration 2 adds first-time setup. Iteration 3 adds explicit sprint picking. Stopping at any iteration leaves a working product, and the agent stops at each checkpoint and hands off to the user for verification (Constitution Principle I).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps to a user story (US1, US2, US3). Setup/Polish tasks have no story label.
- All file paths are repository-root relative.

## Path Conventions

Single-project Python desktop application. Source under `sprint_recap/`, tests under `tests/`, entry script `sprint_recap.py` at repo root. See plan.md "Project Structure / Source Code (repository root)".

---

## Iteration 1: User Story 1 - Generate the recap deck for the just-finished sprint (Priority: P1) 🎯 MVP

**Goal**: With a working folder containing a pptx template, a hand-prepared `sprint-recap.json`, and `YOUTRACK_TOKEN` set, the user double-clicks `sprint_recap.py` and gets a fresh deck beside the template with the dates filled in (long-form English) and the agenda slide populated with every in-sprint issue grouped Finished/Open. The original template is untouched, the output filename is deterministic, and the per-run log file sits beside the deck.

**Independent Test**: Place a template containing the five tokens in a folder with a hand-written `sprint-recap.json` pointing at a YouTrack instance and a closed sprint. Set `YOUTRACK_TOKEN`. Run `python sprint_recap.py`. Confirm: (a) a new pptx appears beside the template, (b) the template's mtime/bytes are unchanged, (c) dates render as e.g. `6 May 2026`, (d) the agenda lists every sprint issue split Finished/Open with subtasks-of-in-sprint-parents collapsed, (e) `<output-stem>.log` exists and contains no token, (f) re-running fires the overwrite prompt.

**Exit criterion**: User Story 1 works end-to-end. The project runs. This iteration absorbs all bootstrap (project layout, single dependency, entry shim, dual-sink logging, YouTrack client, classification/sort/collapse, deck writer, naming, console+tkinter prompts for template selection and overwrite).

### Bootstrap for Iteration 1

- [X] T001 Create source layout: `sprint_recap/__init__.py`, empty `tests/__init__.py`, `tests/unit/__init__.py`, `tests/fixtures/` directory
- [X] T002 [P] Create `requirements.txt` at repo root with single pinned dependency `python-pptx==<latest stable on PyPI>` (per plan.md / Constitution II)
- [X] T003 [P] Create `.gitignore` at repo root: `venv/`, `__pycache__/`, `*.pyc`, `*.log`, `sprint-recap.json`, `*.pptx` excluded only inside `tests/fixtures/` exception (commit fixture pptx)
- [X] T004 [P] Create `README.md` at repo root with setup (venv + `pip install -r requirements.txt`), `YOUTRACK_TOKEN` env-var instructions for bash/zsh/PowerShell/cmd, and the routine-run double-click flow (mirror `quickstart.md`)
- [X] T005 Create entry shim `sprint_recap.py` at repo root: imports `sprint_recap.app`, calls `sprint_recap.app.main()` under `if __name__ == "__main__":`, otherwise empty (Constitution V: associable with system Python for double-click)

### Tests for User Story 1 (write FIRST, must fail before implementation) ⚠️

- [X] T006 [P] [US1] Generate fixture template at `tests/fixtures/template.pptx` containing the five tokens (`{{SPRINT_START}}`, `{{SPRINT_END}}`, `{{RECAP_DATE}}`, `{{AGENDA_FINISHED}}`, `{{AGENDA_OPEN}}`) per `contracts/template-tokens.md`. Generate via a small `tests/fixtures/_build_template.py` script committed alongside the .pptx so the fixture is reproducible.
- [X] T007 [P] [US1] Write unit tests for long-form English date rendering in `tests/unit/test_dates.py`: cases `6 May 2026`, `12 December 2026`, `1 January 2027`; assert no leading zero on day; assert hard-coded English month names (locale-independent) per research §R5.
- [X] T008 [P] [US1] Write unit tests for filename sanitization and pattern in `tests/unit/test_naming.py`: cases from `contracts/output-filename.md` (`Sprint 42`, `Q2/2026 — Recap`, `R&D — week 18`, `🚀 launch sprint`, `🎉🎉🎉` → idReadable fallback); assert deterministic `<template-stem>_<sprint-name>_<sprint-end-YYYY-MM-DD>.pptx` shape.
- [X] T009 [P] [US1] Write unit tests for classification + sort + subtask collapse in `tests/unit/test_classify.py`: Finished iff `resolved_at is not None` (FR-010 — must NOT inspect state-name strings); Finished sorted by `(resolved_at, id_readable)` ascending, Open sorted by `(created_at, id_readable)` ascending (FR-020); subtask collapsed iff `parent_id_readable in sprint_ids` computed against the full pre-filter membership (data-model.md `is_subtask_to_collapse`); empty-sprint case yields empty Finished and Open lists with `unfiltered/filtered/collapsed_subtask` counts intact (FR-015).
- [X] T010 [P] [US1] Write unit tests for token substitution in `tests/unit/test_deck_tokens.py` against `tests/fixtures/template.pptx`: load fixture, substitute the five tokens with sample values, assert (a) date tokens replaced in-place at paragraph level preserving surrounding text, (b) agenda text frame cleared and one paragraph per issue title written in given order, (c) original fixture file bytes unchanged on disk after the test (open via `read_bytes()` snapshot before/after), (d) missing required token (e.g. delete `{{AGENDA_FINISHED}}` from a copy) raises a clear error naming the token (spec edge case), (e) duplicate `{{AGENDA_FINISHED}}` raises an explicit error (template-tokens contract).

### Implementation for User Story 1

- [X] T011 [P] [US1] Implement filename sanitization + pattern builder in `sprint_recap/naming.py`: `output_filename(template_stem, sprint_name, sprint_end_date, idreadable_fallback) -> str` per research §R4 / `contracts/output-filename.md`; helper `output_paths(working_folder, template_path, sprint) -> (output_pptx_path, log_path)`.
- [X] T012 [P] [US1] Implement classification + sort + subtask collapse in `sprint_recap/classify.py`: `build_agenda_plan(issues: list[SprintIssue], type_filter: IssueTypeFilter) -> AgendaPlan` populating `unfiltered_count`, `filtered_count`, `collapsed_subtask_count`, `finished`, `open` per data-model.md invariants and FR-018/FR-019/FR-020; default filter `"all"` is no-op; empty-list filter logged-and-treated-as-`"all"` per data-model.md `IssueTypeFilter` rules.
- [X] T013 [P] [US1] Implement long-form English date rendering AND pptx token substitution in `sprint_recap/deck.py`: `format_long_date(d: date) -> str` (research §R5; hard-coded English month names; no `strftime`); `render_deck(template_path, output_path, sprint, agenda_plan)` that walks every slide / shape / text frame, performs paragraph-level substitution for date tokens, clears+writes agenda text frames per `contracts/template-tokens.md` §"How tokens are filled", validates required-token presence (raises naming missing tokens) and rejects duplicate `{{AGENDA_FINISHED}}` / `{{AGENDA_OPEN}}`; uses paragraph-level run-coalescing trade-off documented in template-tokens contract.
- [X] T014 [P] [US1] Implement dual-sink logging in `sprint_recap/logging_setup.py`: `init_logger()` returns a logger with a `StreamHandler` to stdout immediately and an in-memory buffer for pre-stem records; `attach_file_handler(log_path)` flushes buffered records and switches to live file writes per research §R6; format `YYYY-MM-DD HH:MM:SS LEVEL message` per `contracts/log-file.md`; redaction helper that strips any occurrence of the token from a string (defense in depth, research §R7).
- [X] T015 [US1] Implement settings loader and token reader in `sprint_recap/config.py`: `load_settings(working_folder) -> SavedSettings | None` (returns None on missing/`JSONDecodeError` so caller routes to first-time setup later — but for this iteration, missing settings raises a clear "no `sprint-recap.json` found in this folder; create one matching `contracts/settings-file.md` or run again after Iteration 2 to set it up interactively"); `read_token() -> str` from `YOUTRACK_TOKEN` (raises with explicit "set `YOUTRACK_TOKEN`" guidance per FR-016 if missing/empty); rejects forbidden-key contamination (`token`, `bearer`, `password`, `api_key`) per settings-file.md contract; validates `schema_version == 1`.
- [X] T016 [US1] Implement `SprintIssue`, `Sprint`, `IssueTypeFilter`, `SavedSettings`, `RunInputs`, `AgendaPlan` dataclasses in `sprint_recap/models.py` per data-model.md (single file because each is small and they share imports; not split across modules). Includes derived predicates `is_finished` and `is_subtask_to_collapse`.
- [X] T017 [US1] Implement YouTrack REST client in `sprint_recap/youtrack.py` per `contracts/youtrack-api.md`: `class YouTrackClient(base_url, token, http_get=urllib_get)` exposing one seam per research §R10; methods `verify_project(query) -> Project`, `list_agile_boards() -> list[Board]` (with sprints inlined per the single-call decision in research §R2), `fetch_sprint_issues(board_id, sprint_id) -> list[SprintIssue]` calling `GET /api/agiles/{board_id}/sprints/{sprint_id}` and parsing `issues[].idReadable`, `summary`, `resolved` (epoch ms → datetime, null preserved), `created`, `parent.issues[0].idReadable`, `customFields[name="Type"].value.name` (missing → `"(unknown)"`); URL hygiene per research §R2a (trim trailing slash, reject non-http(s)); error mapping per research §R2b / contracts/youtrack-api.md (URLError, 401/403, 404 project/board, other 4xx, 5xx, non-JSON) producing the exact user-facing strings in that contract.
- [X] T018 [P] [US1] Implement template discovery and basic prompt facade in `sprint_recap/prompts.py`: detect prompt mode once at startup (`sys.stdin.isatty()`) and store in module-level constant per research §R3 / FR-012; expose `find_template(working_folder) -> Path` (zero pptx → prompt user for path or abort; one pptx → use it; multiple pptx → numbered selection in console mode, listbox in tkinter mode); expose `confirm_overwrite(path) -> Literal["overwrite", "save_as", "cancel"]` for FR-004 (in this iteration the "save_as" branch may simply re-prompt for a path inside the working folder; respects FR-013 "no writes outside the working folder unless explicitly redirected"); log the chosen prompt mode line `prompt_mode=console` or `prompt_mode=tkinter` (FR-017).
- [X] T019 [US1] Implement orchestration in `sprint_recap/app.py`: `main()` performs in order — detect working folder (`Path.cwd()` — Constitution III); `init_logger()`; record run header (working folder, prompt mode); `read_token()`; `load_settings()` (raises clear error in this iteration if absent); `find_template()`; build YouTrackClient; pick the latest-by-end-date sprint from boards response (FR-007 — the `archived` flag is ignored); fetch issues by `(board_id, sprint_id)`; build `AgendaPlan` via `classify.build_agenda_plan`; compute output and log paths via `naming.output_paths`; `attach_file_handler(log_path)` (flushes buffered console-only records to file); render deck (handling overwrite prompt before writing per FR-004); write the cross-reference list `id_readable | bucket | title` into the log per `contracts/log-file.md` §8; emit run-footer success line. On any error path, log an ERROR line (paraphrased; never echoes token) and abort without producing partial deck or overwriting existing good output (FR-014).
- [X] T020 [US1] Manual-handoff summary: state in plain language to the user that with `sprint_recap.py` + `requirements.txt` installed, a hand-prepared `sprint-recap.json` (matching `contracts/settings-file.md`), `YOUTRACK_TOKEN` set in their shell, and a tokenized template in the working folder, double-clicking `sprint_recap.py` (or `python sprint_recap.py`) now produces the deck and the per-run log beside the template with the dates and agenda filled in, the original template unchanged, and re-runs triggering the overwrite prompt. Walk the user through `quickstart.md` §"Manual verification at iteration handoffs" as the verification recipe. Do NOT run the program — the user drives verification (Constitution I).

**Checkpoint (Iteration 1)**: User Story 1 works end-to-end with a hand-prepared `sprint-recap.json`. The user verifies per the recipe in `quickstart.md` (deck dates correct, agenda matches sprint, original template byte-identical, log contains no token, prompt-mode line present, cross-reference list covers every issue). The user decides whether to continue, refine, or stop.

---

## Iteration 2: User Story 2 - First-time setup of the YouTrack connection (Priority: P2)

**Goal**: A fresh working folder (no `sprint-recap.json`) with `YOUTRACK_TOKEN` set walks the user through prompts for YouTrack URL, project, and (only when the project has more than one visible board) board, verifies the connection against the live YouTrack instance, and saves the non-token settings to `sprint-recap.json` before continuing into the recap flow built in Iteration 1. On the next run, no setup prompts appear.

**Independent Test**: In a fresh folder with no `sprint-recap.json` and `YOUTRACK_TOKEN` set, run `python sprint_recap.py`. Confirm: prompts ask URL → project → board (skipped if exactly one); on success a `sprint-recap.json` appears (atomic write; no token field; `schema_version=1`; `issue_type_filter="all"`); the program proceeds to produce a deck (Iteration 1 flow). On a second run in the same folder, no setup prompts appear. Verify failure paths: missing `YOUTRACK_TOKEN` aborts with explicit guidance and does NOT create `sprint-recap.json`; an unreachable URL or rejected token aborts with the contracts/youtrack-api.md error message and does NOT create `sprint-recap.json` (FR-005, FR-014); a project with zero visible Agile boards reports the FR-005 edge case and does NOT save settings.

**Exit criterion**: User Story 2 works end-to-end on top of Iteration 1. A configured folder still behaves exactly as in Iteration 1; an unconfigured folder gets walked through setup. The project still runs end-to-end.

### Tests for User Story 2 (write FIRST, must fail before implementation) ⚠️

- [X] T021 [P] [US2] Write unit tests for atomic settings write in `tests/unit/test_config.py`: `save_settings()` writes via `sprint-recap.json.tmp` then `os.replace`; never persists `YOUTRACK_TOKEN` or any field in the forbidden-key set; rejects `schema_version != 1` on load; treats `issue_type_filter == []` as `"all"` with a logged WARN (data-model.md `IssueTypeFilter`); a process killed mid-write does NOT leave a half-written `sprint-recap.json` (simulated by writing to `.tmp` and asserting target file is absent or holds the prior good content).
- [X] T022 [P] [US2] Write unit tests for prompt facade in `tests/unit/test_prompts.py`: console mode (mock `sys.stdin.isatty()` True) numbered-list selection returns the chosen item; tkinter mode (mock isatty False, mock `tkinter.simpledialog`/`tkinter.Listbox`/`tkinter.messagebox`) returns the chosen item; the chosen mode is computed once and module-level (FR-012 / research §R3); cancel returns the cancel sentinel and the caller is expected to abort without writing files (FR-016, FR-014).
- [X] T023 [P] [US2] Write unit tests for YouTrack client setup-flow methods in `tests/unit/test_youtrack_setup.py`: stubbed `http_get` returning recorded fixtures under `tests/fixtures/youtrack/` for (a) project lookup happy path / 404 / multiple matches, (b) agile-boards listing with 0/1/many boards visible to the project; assert error mapping produces the exact user-facing strings from `contracts/youtrack-api.md` "Error mapping".

### Implementation for User Story 2

- [X] T024 [P] [US2] Extend `sprint_recap/config.py`: implement `save_settings(working_folder, settings)` (atomic `.tmp` + `os.replace`; `json.dump(..., indent=2, sort_keys=True, ensure_ascii=False)`; never writes token or any forbidden-key field per `contracts/settings-file.md`); ensure `load_settings` already gracefully reports `JSONDecodeError` as un-configured (US2-trigger condition).
- [X] T025 [P] [US2] Extend `sprint_recap/prompts.py` with the full tkinter facade (research §R3): `simpledialog.askstring` for free-text URL/project entry, `tkinter.Listbox` inside a `tkinter.Toplevel` for board/sprint selection, `messagebox.showerror` for fatal errors, `messagebox.askyesnocancel` for confirmations; expose `prompt_text(label, default=None, secret=False) -> str | None`, `prompt_choice(label, options) -> str | None`. Console-mode equivalents using `input()` and numbered lists. The `secret=True` path is reserved for any future use; the token is NEVER prompted (FR-016 — read from env only).
- [X] T026 [US2] Extend `sprint_recap/youtrack.py` with the setup-flow endpoints per `contracts/youtrack-api.md` §1–§2: `verify_project(query)` (GET `/api/admin/projects?fields=id,name,shortName&query=…`; map 0 results = not visible / 1 = candidate / many = disambiguation list); `list_agile_boards()` (GET `/api/agiles?fields=id,name,projects(id,shortName),sprints(id,name,start,finish,archived)&$top=100`; client-side filter by project id) returning the boards-with-sprints structure used by both US2 (board picker) and US3 (sprint picker). [Already implemented in Iteration 1; verified by T023 tests against the contract.]
- [X] T027 [US2] Add first-time-setup orchestration to `sprint_recap/app.py`: when `load_settings()` returns None, run `first_time_setup(working_folder, prompts, token)`: prompt YouTrack URL (validate scheme, trim trailing slash); call `verify_project` until it resolves to exactly one project (re-prompt on 0/many); call `list_agile_boards`, default if exactly one, prompt to choose if multiple, error+abort if zero (FR-005 edge case — settings NOT saved per FR-014); on success, build a `SavedSettings` with `schema_version=1`, `issue_type_filter="all"`, `last_sprint_id=None`, and call `save_settings`. Then continue into the Iteration-1 flow without re-fetching boards (reuse the response). Every prompt and verification result is logged per `contracts/log-file.md` §10.
- [X] T028 [US2] Wire missing-token handling end-to-end: when `read_token()` raises, render the FR-016 error (`YOUTRACK_TOKEN not set — see README.md`) via the active prompt mode (console: stderr line; tkinter: `messagebox.showerror`); log ERROR line; abort BEFORE any HTTP call and BEFORE writing settings. Add platform-specific guidance to README.md "Common errors" matching `quickstart.md`.
- [X] T029 [US2] Manual-handoff summary: state to the user that a fresh folder with only the template and `YOUTRACK_TOKEN` set now walks them through URL/project/board prompts, saves `sprint-recap.json` atomically (no token), and proceeds into the Iteration-1 deck flow; subsequent runs in that folder skip setup. Walk through US2 acceptance scenarios as the verification recipe (fresh folder with valid setup → deck produced; missing token → clear error, no settings file; unreachable URL → clear error, no settings file; second run → no re-prompt). Do NOT run the program — the user drives verification.

**Checkpoint (Iteration 2)**: User Stories 1 and 2 are exercisable end-to-end. The user verifies fresh-folder setup, error paths that must NOT create `sprint-recap.json`, and the no-prompt second run. The user decides whether to continue.

---

## Iteration 3: User Story 3 - Pick a different sprint than the most-recent one (Priority: P3)

**Goal**: The user can launch the program in a "pick a sprint" mode to recap a sprint other than the latest-by-end-date default — choosing from a list of sprints from the configured board with their dates — and the resulting deck reflects the picked sprint.

**Independent Test**: With a configured folder and a board that has more than one closed sprint, run `python sprint_recap.py --pick-sprint`. Confirm the program lists all sprints from the configured board with their dates, lets the user pick one, and produces a deck whose dates and stories come from the picked sprint (not the default). With one closed sprint only, the picker still appears and lists that one sprint. Cancelling at the picker writes no files.

**Exit criterion**: User Stories 1, 2, 3 are exercisable end-to-end. The default no-arg flow remains the latest-by-end-date sprint (FR-007); `--pick-sprint` flips into the picker.

### Tests for User Story 3 (write FIRST, must fail before implementation) ⚠️

- [X] T030 [P] [US3] Extend `tests/unit/test_prompts.py` with sprint-picker test: given a list of `Sprint` records, the picker presents them sorted by end date descending (most recent first) with each line showing `name (YYYY-MM-DD → YYYY-MM-DD)`; selection returns the chosen `Sprint`; cancel returns the cancel sentinel.
- [X] T031 [P] [US3] Add a CLI-args test in `tests/unit/test_app_args.py`: parsing `--pick-sprint` sets the orchestration into pick-sprint mode; bare invocation (no args) keeps the default flow.

### Implementation for User Story 3

- [X] T032 [US3] Add CLI flag handling to `sprint_recap/app.py` using `argparse` (stdlib): single `--pick-sprint` boolean flag (no other flags in scope for v1). Default flow unchanged.
- [X] T033 [US3] Add `prompt_sprint(sprints) -> Sprint | None` to `sprint_recap/prompts.py`: console mode renders a numbered list `name (start_iso → end_iso)`; tkinter mode renders a `Listbox` with the same labels; sorted by end date descending (latest first) so the FR-007 default sprint is at index 0 visually.
- [X] T034 [US3] Wire the picker into `sprint_recap/app.py`: when `--pick-sprint` is set, after settings/board are resolved, call `prompt_sprint(board.sprints)` (using the already-fetched sprints from the agile-boards response — no extra round-trip); on cancel, abort without writing files; on selection, use that sprint instead of the FR-007 default. Log the chosen sprint id and name per `contracts/log-file.md` §10.
- [X] T035 [US3] Manual-handoff summary: state to the user that `python sprint_recap.py --pick-sprint` now opens a sprint picker showing every sprint on the configured board with its dates, and produces a deck for the chosen one. Walk through US3 acceptance scenarios as the verification recipe. Do NOT run the program — the user drives verification.

**Checkpoint (Iteration 3)**: All three user stories are exercisable end-to-end. The user verifies the picker UX in both prompt modes and confirms cancel writes nothing. The user decides whether to proceed to Polish.

---

## Final Iteration: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that span all three user stories, applied only after the iteration ladder above has been exercised by the user. Every change here must keep the project running end-to-end.

- [ ] T036 [P] Token-redaction audit: grep all of `sprint_recap/` and `tests/` for any code path that could include `YOUTRACK_TOKEN`, request headers, or full URL with auth in a log message, an exception string the program raises, or any file the program writes (settings, log, output). Verify the audit findings are zero per FR-016 / research §R7 / `contracts/log-file.md` "Forbidden content".
- [ ] T037 [P] Determinism audit: for one fixed `(template, sprint, issues)` input, run `render_deck` twice into different output paths and assert the two output `.pptx` files have identical XML body content (unzip and compare); confirm filename-builder produces identical bytes across re-runs (FR-003, research §R9).
- [ ] T038 [P] Expand `README.md` with "Editing the issue-type filter" section documenting how the user hand-edits `issue_type_filter` in `sprint-recap.json` between runs (FR-018), the `"all"` default, and the empty-list-is-treated-as-`"all"` warning behavior.
- [ ] T039 [P] Expand `README.md` "Common errors" table to mirror `quickstart.md` (token-missing, unreachable URL, token rejected, project not visible, missing template tokens, output-already-exists prompt).
- [ ] T040 Verify `contracts/log-file.md` §"Required content" coverage end-to-end by running through the log produced by a sample successful run and a sample error run; ensure all 12 required line categories appear (run header, YouTrack target without token, sprint selection, issue retrieval, filter application, subtask collapse, final split, cross-reference list, output filename, prompts surfaced, errors, run footer).
- [ ] T041 Manual-handoff summary: state to the user that all three user stories run end-to-end with the polish items above completed; no further iterations are scheduled. Do NOT run the program — the user drives verification.

---

## Dependencies & Execution Order

### Iteration Dependencies

- **Iteration 1 (US1 / MVP)**: No prior dependencies. Absorbs all bootstrap (project layout, single dependency `python-pptx`, entry shim, dual-sink logging, YouTrack client read path, classification/sort/collapse, deck writer, naming, console+tkinter prompts for template selection and overwrite). Must run end-to-end with US1 exercisable using a hand-prepared `sprint-recap.json`.
- **Iteration 2 (US2)**: Depends on Iteration 1. Adds first-time-setup interactive flow and atomic settings write. Project still runs end-to-end.
- **Iteration 3 (US3)**: Depends on Iteration 2. Adds `--pick-sprint` flag and sprint picker (reuses Iteration 2's already-fetched boards-with-sprints response — no extra round-trip). Project still runs end-to-end.
- **Final Iteration (Polish)**: Depends on all three user-story iterations being complete and user-verified.

### Within Each Iteration

- Tests are written and failing BEFORE the corresponding implementation (plan.md §R10).
- Models (`sprint_recap/models.py`) before the modules that import them.
- Pure-function modules (`naming.py`, `classify.py`, `deck.py` formatting helpers) before the modules that orchestrate them.
- Settings/config and YouTrack client before `app.py` orchestration.
- The final task of every iteration is a brief user-perspective summary; the user, not the agent, runs and verifies the product.
- Do not move to the next iteration until the user has exercised the current one (Constitution Principle I).

### Parallel Opportunities

- Within Iteration 1 bootstrap: T002, T003, T004 are different files and parallelize.
- Within Iteration 1 tests: T006, T007, T008, T009, T010 are different files and parallelize.
- Within Iteration 1 implementation: T011 (`naming.py`), T012 (`classify.py`), T013 (`deck.py`), T014 (`logging_setup.py`), T018 (`prompts.py`) are different files and parallelize. T015 (`config.py`) and T016 (`models.py`) are different files but T015 imports from T016 — write T016 first, then T015 in parallel with the others. T017 (`youtrack.py`) and T019 (`app.py`) are sequential after the rest.
- Within Iteration 2 tests: T021, T022, T023 are different files and parallelize.
- Within Iteration 2 implementation: T024 (`config.py` extension), T025 (`prompts.py` extension) parallelize. T026 (`youtrack.py` extension) is on its own. T027–T028 sequence after the above.
- Within Iteration 3 tests: T030, T031 are different files and parallelize.
- Final Iteration: T036, T037, T038, T039 parallelize (different concerns).
- Iterations themselves are sequential — never parallelize across iteration boundaries (each iteration must run end-to-end before the next begins).

---

## Parallel Example: User Story 1

```bash
# Bootstrap (after T001 creates the layout):
Task: "Create requirements.txt with python-pptx pin"
Task: "Create .gitignore at repo root"
Task: "Create README.md at repo root"

# Tests (write FIRST, must fail):
Task: "Generate fixture template at tests/fixtures/template.pptx"
Task: "Unit tests for date rendering in tests/unit/test_dates.py"
Task: "Unit tests for filename sanitization in tests/unit/test_naming.py"
Task: "Unit tests for classification + sort + collapse in tests/unit/test_classify.py"
Task: "Unit tests for token substitution in tests/unit/test_deck_tokens.py"

# Pure-function implementation modules (after T016 models exist):
Task: "Implement filename sanitization in sprint_recap/naming.py"
Task: "Implement classification/sort/collapse in sprint_recap/classify.py"
Task: "Implement date rendering + deck token substitution in sprint_recap/deck.py"
Task: "Implement dual-sink logging in sprint_recap/logging_setup.py"
Task: "Implement template-discovery + overwrite prompts in sprint_recap/prompts.py"
```

---

## Implementation Strategy

### MVP First

1. Complete Iteration 1: from empty repo to a runnable program that, given a hand-prepared `sprint-recap.json` and `YOUTRACK_TOKEN`, produces the deck and the per-run log. This is the smallest user-visible slice that delivers the spec's headline value, and it absorbs all bootstrap.
2. **STOP and EXERCISE**: user runs Iteration 1 against their real working folder per the recipe in `quickstart.md` §"Manual verification at iteration handoffs", confirms the deck and log are correct, and decides whether to continue.

### Incremental Delivery

1. Complete Iteration 1 → user exercises it (MVP).
2. Complete Iteration 2 → user exercises first-time setup including all error paths that must NOT create `sprint-recap.json`.
3. Complete Iteration 3 → user exercises `--pick-sprint` against a board with multiple closed sprints.
4. Complete Final Iteration → user re-exercises all three flows after polish.

Each iteration adds one user story without breaking the prior ones. Stopping at any iteration leaves a working product covering one or more user stories.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks.
- [Story] label maps each task to its user story for traceability; setup/polish tasks have no story label per template rules.
- Every iteration ends with the project in a runnable state; do not move forward until the user has exercised the current iteration (Constitution Principle I).
- Tests are required for the deterministic, pure-function pieces enumerated in plan.md §R10. The agent does NOT write integration tests against a real YouTrack — the YouTrack client exposes a single `http_get` seam for stubbing (research §R10).
- The agent does NOT run the product at iteration boundaries; the user verifies.
- The `YOUTRACK_TOKEN` is read from the environment at the start of every run and never persisted; settings are written atomically via `.tmp` + rename; the original template is treated as read-only across all iterations.
