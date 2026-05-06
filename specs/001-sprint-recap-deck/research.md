# Phase 0 Research: Sprint Recap Deck Generator

The spec is fully clarified — there are no `NEEDS CLARIFICATION` markers in
the Technical Context. This file resolves the remaining technical questions
that come up when translating the spec into code: which library calls to use,
which YouTrack endpoints to hit, how to recognize the launch mode, and how to
keep the program safe and deterministic. Each item below is recorded as
**Decision / Rationale / Alternatives considered**.

## R1. Pptx editing library and token-substitution strategy

- **Decision**: Use `python-pptx` (latest stable on PyPI; pin in
  `requirements.txt`). Walk every slide, every shape, every text frame,
  every paragraph, every run; do exact-string substitution on the literal
  token strings (`{{SPRINT_START}}`, `{{SPRINT_END}}`, `{{RECAP_DATE}}`,
  `{{AGENDA_FINISHED}}`, `{{AGENDA_OPEN}}`).
- **Rationale**: pptx is a zipped Office Open XML format; correctly
  preserving slide layouts, masters, theme, autofit settings, and the
  template's text-frame body properties is materially harder than the work
  `python-pptx` already does. Per Constitution Principle II, this clears
  both the "broadly recognized" and "high value vs. hand-rolling" bars.
  Working at the run level (not the paragraph string level) preserves
  formatting, but the spec's tokens are intended to be the only content of
  their text frame (or at least their paragraph), so a paragraph-level
  exact-match replacement is sufficient and is what we will document in the
  template-tokens contract.
- **Alternatives considered**:
  - Hand-rolled zip + XML editing with stdlib `zipfile` + `xml.etree`.
    Rejected: every regression in pptx structure (autofit attributes,
    a:rPr namespacing, list bullets, master-vs-layout overrides) becomes a
    bug to debug. Not worth the dependency saved.
  - `Aspose.Slides`, `python-pptx-templater`, etc. Rejected: niche or
    proprietary; fail Principle II.

### R1a. How agenda lists are written into the agenda text frames

- **Decision**: When `{{AGENDA_FINISHED}}` (or `{{AGENDA_OPEN}}`) is found
  inside a text frame, the program clears that text frame and writes one
  paragraph per issue title in the chosen sort order (FR-020). The first
  paragraph reuses the existing run's formatting where possible (so the
  template's chosen font, size, bullet style carry over); subsequent
  paragraphs are added with `text_frame.add_paragraph()` and inherit the
  text frame's body properties, which is also where pptx autofit lives.
- **Rationale**: Honors the spec's "single agenda slide; visual fit
  delegated to the template's text-frame autofit" decision (FR-010). It
  avoids us re-implementing autofit ourselves, which `python-pptx`
  intentionally does not compute (PowerPoint computes it at render time
  from `bodyPr` flags such as `normAutofit`).
- **Alternatives considered**: Replacing only the token's run (leaving
  surrounding text in the same frame). Rejected: the spec says these
  tokens denote the entire agenda region, so co-mingled text in the same
  frame would be unexpected and confusing. Documented in the
  template-tokens contract.

## R2. YouTrack REST API endpoints used

YouTrack exposes a REST API rooted at `<baseUrl>/api`. We will call it with
`urllib.request` plus a small helper for `Authorization: Bearer <token>`,
JSON encoding/decoding, and error mapping. Documented endpoints we depend
on (the full contract appears in `contracts/youtrack-api.md`):

- **Project lookup** —
  `GET /api/admin/projects?fields=id,name,shortName&query=<user-input>`
  (or, when the user pastes a project shortName, a direct
  `GET /api/admin/projects/<projectId>?fields=...`). Used during first-time
  setup to verify the project is visible to the token.
- **Agile boards for project** —
  `GET /api/agiles?fields=id,name,projects(id,shortName),sprints(id,name,start,finish,archived)&projectId=<id>`
  (filter client-side by projects containing the selected project). Used
  to enumerate visible boards for FR-005's "exactly-one-board → default,
  many → prompt" rule, and to enumerate sprints for FR-007 / US3.
- **Issues in a sprint** —
  `GET /api/agiles/<boardId>/sprints/<sprintId>?fields=issues(idReadable,summary,resolved,created,parent(issues(idReadable)),customFields(name,value(name)))`
  The board and sprint are addressed by id (already known from the
  agile-boards response above), so the endpoint returns the issues
  attached to that exact sprint without going through the search-query
  language. An earlier draft used `GET /api/issues?query=Board {board}: {sprint}`;
  that approach was rejected because the search parser rejects multi-word
  board names and the `Board:` attribute filter does not consistently
  restrict by board context across YouTrack versions. The endpoint has no
  `$top` parameter and returns every issue in the sprint in one response;
  no paging is currently required (typical sprints are well under any
  practical ceiling).
- **Issue type** — comes from the issue's `Type` custom field, present in
  the `customFields` list. We extract `value.name` (e.g., "Story", "Bug",
  "Task") for FR-018 filtering.
- **Parent reference for FR-019** — comes from the issue's `parent`
  link container. The `parent.issues` array contains the parent issue's
  `idReadable`; we treat presence-and-in-sprint as the trigger to collapse.

- **Decision summary**:
  - Use one `GET /api/agiles?...` call per run to fetch board metadata
    (cheap; lets us list sprints without a second round-trip).
  - Use one `GET /api/agiles/<boardId>/sprints/<sprintId>?...` call per
    run to fetch the sprint's issues with all needed fields in one shot
    (idReadable, summary, resolved, created, parent, customFields(Type)).
  - All requests use `Authorization: Bearer ${YOUTRACK_TOKEN}` and
    `Accept: application/json`.
- **Rationale**: Two GETs per run keeps the implementation simple, fits
  inside the under-1-minute SC-001 budget on any reasonable network, and
  uses only documented YouTrack public API surface that has been stable
  for years.
- **Alternatives considered**:
  - Using a higher-level YouTrack Python client. Rejected: third-party
    clients are niche and would fail Principle II for a workload of two
    GETs.
  - Routing the issues fetch through `GET /api/issues?query=Board {board}: {sprint}`.
    Rejected after live testing: the search parser returns HTTP 400 on
    multi-word board names, and the `Board:` attribute filter did not
    consistently restrict by board context across YouTrack versions —
    `Board: {name}` returned zero matches even on populated sprints. The
    per-sprint endpoint above sidesteps the search-query language
    entirely and is the documented YouTrack way to list a sprint's
    issues by id.
  - Paging the issues endpoint. Rejected for v1: our scale assumption
    (≤ ~100 issues per sprint) is far below any practical ceiling, and
    paging adds nontrivial code surface. Documented as a future revisit
    if a sprint ever exceeds the cap (the `$top` value will be visible
    in the per-run log).

### R2a. URL hygiene

- **Decision**: Treat the user-supplied YouTrack URL as the base; trim a
  trailing slash; do not silently append/strip `/api`. Reject URLs whose
  scheme is not `http` or `https`. Build endpoint URLs by joining `base + "/api/" + path`.
- **Rationale**: Avoids the classic "did the user give us the UI URL or
  the API URL?" confusion and keeps the verification step (FR-005)
  predictable.

### R2b. Error surface

- **Decision**: Map common HTTP/`urllib` errors to short, plain-language
  user messages: connection refused / DNS failure / timeout → "Could not
  reach YouTrack at <url>"; 401/403 → "Token rejected — check
  `YOUTRACK_TOKEN`"; 404 on project/board → "Project/board not visible
  to this token"; other 4xx/5xx → "YouTrack error <status>: <body
  excerpt>". Per FR-014, no partial deck is produced and no existing good
  output is overwritten on these paths.
- **Rationale**: Constitution IV (Conversational Fallback) — surface the
  failure plainly; do not silently fall back.

## R3. Prompt-mode auto-detection (console vs `tkinter`)

- **Decision**: At program start, evaluate `sys.stdin.isatty()` exactly
  once. If True, the run uses console prompts (`input()` for free text;
  numbered list selection; y/n confirmations). If False, the run uses
  stdlib `tkinter` (`simpledialog.askstring` for text;
  `tkinter.Listbox` inside a small `Toplevel` for selection;
  `messagebox.showerror` / `askyesnocancel` for confirmations). The chosen
  mode is captured in a module-level variable, written to the per-run log
  as either `prompt_mode=console` or `prompt_mode=tkinter`, and not
  re-evaluated mid-run.
- **Rationale**: Matches the spec verbatim (FR-012). Doing the detection
  exactly once avoids the inconsistency of mid-run mode flips, which can
  happen if a child process redirects stdin.
- **Alternatives considered**:
  - Always use `tkinter`. Rejected: terminal users on macOS/Linux
    typically don't want a GUI popping up; it also fails CI/headless
    use.
  - Always use console. Rejected: a Windows double-click without an
    attached console produces no visible prompt at all — the program
    appears hung from the user's point of view.

## R4. Filename sanitization for the sprint-name segment

- **Decision**: For `<sprint-name>` in the FR-003 pattern, replace any
  character outside `[A-Za-z0-9._-]` with `_`, collapse runs of `_`,
  strip leading/trailing `_`. Preserve case. Empty result → fall back
  to the sprint's id-readable slug from YouTrack.
- **Rationale**: Produces deterministic, filesystem-safe names on
  Windows, macOS, and Linux without depending on a third-party
  slugifier. Determinism matters for FR-003's "re-run produces the same
  filename → triggers FR-004 overwrite prompt".
- **Alternatives considered**:
  - Lowercasing. Rejected: would surprise users whose sprints are named
    "Sprint 42" and would unnecessarily diverge from the YouTrack UI
    label.
  - `python-slugify`. Rejected: another dependency for ~10 lines of
    code; fails Principle II.

## R5. Date rendering in the deck (long-form English)

- **Decision**: Render `{{SPRINT_START}}`, `{{SPRINT_END}}`, and
  `{{RECAP_DATE}}` using `f"{day} {month_name} {year}"` where `day` is
  `int(d.day)` (no leading zero), `month_name` is hard-coded English
  (`["January", ..., "December"]`), and `year` is `d.year`. We do not
  use `strftime("%B")` because that is locale-dependent and could yield
  e.g. "Mai" on a Norwegian system, which the spec rules out.
- **Rationale**: Matches FR-009 verbatim (`6 May 2026`,
  `12 December 2026`). Avoids locale leaks. Hard-coded English month
  names are eight lines of code — well below Principle II's bar for
  introducing a dependency like `babel`.
- **Alternatives considered**:
  - `datetime.strftime("%-d %B %Y")` on POSIX. Rejected: not portable
    to Windows (no `%-d`), and locale-sensitive.
  - `babel.dates.format_date(d, "d MMMM y", locale="en")`. Rejected:
    third-party dependency for a one-liner.

## R6. Dual-sink logging (file + console)

- **Decision**: Configure the standard `logging` module with two
  handlers: a `FileHandler` writing to `<output-stem>.log` in the
  working folder, and a `StreamHandler` writing to `stdout`. The output
  stem is known only after we know the sprint (it's part of the
  filename per FR-003), so the program buffers early log records to an
  in-memory list and flushes them to the file once the stem is computed.
  Pre-stem records still go to the console handler immediately.
- **Rationale**: Honors FR-017's "per-run log file `<output-stem>.log`
  in the working folder, plus the same content streamed to console"
  while accepting that the stem is not knowable until we have the
  sprint dates.
- **Alternatives considered**:
  - Using a temp filename then renaming. Rejected: introduces a brief
    window where a partial `recap.log.tmp` exists in the working
    folder, which violates the spirit of "the program produces files
    deterministically named per FR-003".
  - Logging to stdout only and asking the user to redirect. Rejected:
    fails Constitution III (folder-as-context) for double-click users.

## R7. Token redaction in logs and errors

- **Decision**: Read `YOUTRACK_TOKEN` once at startup; store the value
  only in a module-level constant inside the YouTrack client; never
  include it in any log statement, exception message that we raise, or
  HTTP error body we surface. When we surface a YouTrack 401/403 error,
  we paraphrase ("Token rejected — check `YOUTRACK_TOKEN`") rather than
  echoing the request that contained the bearer header.
- **Rationale**: FR-016. Defensive: even if a third-party library logs
  request headers, we want a single source of truth for the token, kept
  out of any string we ourselves emit.

## R8. Settings file format and lifecycle

- **Decision**: Store settings as a JSON file named `sprint-recap.json`
  in the working folder, loaded with `json.load`, written with
  `json.dump(..., indent=2, sort_keys=True)`. Schema captured in
  `contracts/settings-file.md`. The token is never a key. Saved only
  after FR-005's verification step succeeds; on any first-time-setup
  error path the file is not created (FR-005 ¶3, FR-014).
- **Rationale**: JSON is stdlib, human-editable (FR-018 says the user
  can edit the issue-type filter between runs), and round-trips
  losslessly. `indent=2 + sort_keys=True` makes diffs readable for the
  user who edits the file by hand.
- **Alternatives considered**:
  - `tomllib` for read + `tomli_w` for write. Rejected: writer is a
    third-party dependency that fails Principle II for ~5 keys.
  - INI via `configparser`. Rejected: nested types (the issue-type
    filter list) don't round-trip cleanly.
  - Environment variables for everything. Rejected: violates the
    spec's "saved per folder so subsequent runs need no setup" (FR-006)
    and the constitution's folder-as-context principle.

## R9. Determinism of repeated runs

- **Decision**: All ordering inputs are explicit: Finished list sorted
  by `(resolved_timestamp, idReadable)`, Open list sorted by
  `(created_timestamp, idReadable)`, both ascending (FR-020). Filename
  is fully derived from `(template-stem, sprint-name, sprint-end-date)`
  (FR-003). Long-form date is locale-independent (R5). No randomness,
  no `time.time()` baked into outputs, no UUIDs in filenames.
- **Rationale**: Makes the FR-004 overwrite prompt actually fire on a
  re-run, makes diffs of two runs of the same sprint show only the
  intentional changes, and makes the test suite stable.

## R10. Testing scope

- **Decision**: Unit-test the deterministic, pure-function pieces:
  classification + sort (R9, FR-010, FR-019, FR-020), filename
  sanitization (R4), date rendering (R5), and a token-substitution
  smoke test against a tiny fixture pptx generated once and committed
  under `tests/fixtures/template.pptx`. Do NOT write integration tests
  against a real YouTrack — instead, the YouTrack client takes a
  pluggable HTTP-callable seam (a thin wrapper around `urllib.request`)
  so unit tests can stub it. End-to-end runs are the user's
  verification job at iteration boundaries (Constitution I).
- **Rationale**: Maximum coverage of the parts most likely to break
  silently (date formatting, sort order, filename hashing-of-meaning),
  zero coupling to a live YouTrack instance, and respect for the
  iteration-handoff contract.
- **Alternatives considered**:
  - Mock the entire program flow end-to-end. Rejected as
    over-engineered for a single-user monthly tool; the fixtures and
    mocks would dwarf the code under test.
  - Skip tests entirely. Rejected: the deterministic pieces above are
    exactly the ones a future reader would mis-edit, and they are
    cheap to test.

---

All Phase 0 questions resolved. Proceeding to Phase 1.
