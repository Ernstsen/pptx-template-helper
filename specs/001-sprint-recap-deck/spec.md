# Feature Specification: Sprint Recap Deck Generator

**Feature Branch**: `001-sprint-recap-deck`
**Created**: 2026-05-06
**Status**: Draft
**Input**: User description: "I have a pptx template that i copy-paste once a month when a scrum-sprint is done. I then replace dates, and run thorugh user-stories in youtrack to fill out the agenda with the user stories from the sprint, and their respective status. I need a program that automatically copies the pptx to a new file, loads the information from a sprint in youtrack, updates all dates, and fills out the slide with open and finished tasks"

## Clarifications

### Session 2026-05-06

- Q: How should the recap-meeting date placeholder in FR-009 be filled? → A: Use the sprint's end date; no separate meeting-date concept.
- Q: How is the YouTrack access token stored? → A: Read from an environment variable; never persisted to disk by the program.
- Q: How are stories classified Finished vs Open across customized workflows? → A: Use YouTrack's built-in `resolved` attribute on the issue; resolved → Finished, otherwise Open. No first-time-setup mapping prompt.
- Q: What is the output filename pattern? → A: `<template-stem>_<sprint-name>_<sprint-end-YYYY-MM-DD>.pptx`.
- Q: Where do logs go? → A: Per-run log file `<output-stem>.log` in the working folder, plus the same content streamed to console.
- Q: Which YouTrack issue types appear on the agenda? → A: Configurable per folder (saved with other settings); default includes all issue types found in the sprint.
- Q: How are subtasks handled on the agenda? → A: Only top-level issues appear; subtasks whose parent is also in the sprint are excluded. Subtasks whose parent is NOT in the sprint are treated as top-level.
- Q: How is each agenda entry rendered on the slide? → A: Title only; no YouTrack issue ID on the slide. (IDs still appear in the per-run log for cross-checking.)
- Q: In what order are issues listed within the Finished and Open groups? → A: Finished sorted ascending by `resolved` timestamp; Open sorted ascending by created date.
- Q: What is the name of the token environment variable? → A: `YOUTRACK_TOKEN`.
- Q: How does the program recognize placeholders in the pptx template? → A: Named text tokens (`{{SPRINT_START}}`, `{{SPRINT_END}}`, `{{RECAP_DATE}}`, `{{AGENDA_FINISHED}}`, `{{AGENDA_OPEN}}`) inserted into the template; the program scans text frames and replaces matches. No interactive mapping or shape-name conventions.
- Q: How does the program identify which YouTrack sprint to read? → A: User supplies project + Agile board within that project; the board owns the sprints. If the project has exactly one visible board, the program defaults to it; if more than one, the user is prompted to choose. The chosen board is saved with the other settings.
- Q: What date format is substituted into the date tokens in the rendered deck? → A: Long-form English, day-month-year, no leading zero on the day, full English month name, four-digit year (e.g., `6 May 2026`). The filename pattern continues to use ISO `YYYY-MM-DD` per FR-003 — only the in-deck rendering uses long form.
- Q: How should the program behave when an agenda group has more issues than fit on the slide? → A: Single agenda slide; the program writes every entry faithfully and delegates visual fit to the autofit behaviour of the template's text frames. No slide duplication, entry capping, or overflow warnings beyond the per-run counts already in the log.
- Q: How does the program present prompts to the user when it needs interactive input? → A: Auto-detect at startup — console prompts (`input()`, numbered selection lists) when standard input is a TTY; minimal stdlib `tkinter` dialogs (text entry, listbox, message box) otherwise. The mode is chosen once per run and applies to all prompts in that run; the per-run log records which mode was used.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate the recap deck for the just-finished sprint (Priority: P1)

A scrum-team member finishes a sprint and needs a presentation deck for the recap
meeting. They drop the existing pptx template into a working folder together with the
program, launch the program, and within a minute they have a fresh pptx file in the
same folder where the dates have been updated and the agenda slide lists every user
story from the sprint, split into "Finished" and "Open". They open the deck and only
do light cosmetic touch-ups — none of the data entry that used to take them most of
an hour.

**Why this priority**: This is the core monthly task the user is automating today.
Without this story working end-to-end the program has no value; with it, the user can
already replace their manual workflow.

**Independent Test**: With a template pptx and a closed sprint in YouTrack containing
a known set of user stories, run the program and confirm: a new pptx is produced
beside the template, the original template is untouched, the deck's date placeholders
match the sprint's dates, and the agenda slide contains every story from the sprint
with the correct Finished/Open grouping.

**Acceptance Scenarios**:

1. **Given** the working folder contains exactly one pptx template and the program is
   already configured against a YouTrack instance with a recently closed sprint,
   **When** the user double-clicks the program, **Then** a new pptx file is created
   in the same folder with the sprint's dates filled in and the agenda slide
   populated with every user story from that sprint, grouped into Finished and Open.
2. **Given** the sprint has a mix of Done and not-Done stories, **When** the deck is
   produced, **Then** every Done story appears under "Finished", every not-Done story
   appears under "Open", and the counts in the deck match the sprint exactly.
3. **Given** the original template file, **When** the program has finished, **Then**
   the original template file is byte-for-byte unchanged on disk.
4. **Given** an output file with the intended name already exists in the folder,
   **When** the program is about to write it, **Then** the user is asked whether to
   overwrite, save under a new name, or cancel — and nothing is written until the
   user answers.

---

### User Story 2 - First-time setup of the YouTrack connection (Priority: P2)

The first time the user runs the program in a folder, it does not yet know which
YouTrack instance, project, or sprint to read from. The program detects this and
prompts the user — through a console prompt or a simple dialog — for the YouTrack
URL, an access token, the project, the Agile board within that project (skipped
when the project has exactly one visible board), and (if more than one fits) the
sprint to recap.
It saves these answers locally so subsequent runs need no setup.

**Why this priority**: Without this, the user can't get past the first run. It is
needed before US1 truly delivers, but it only happens once per folder, so it ranks
below the recurring core flow.

**Independent Test**: In a folder that has never been configured, run the program
and confirm: the program asks for YouTrack URL, token, project, board (when the
project has more than one), and sprint selection; on completion it saves those
non-token settings to the folder; on a follow-up run in the same folder it does
not ask again.

**Acceptance Scenarios**:

1. **Given** a fresh working folder with no saved YouTrack settings and the token
   environment variable set, **When** the program is launched, **Then** it prompts
   the user for the YouTrack URL, the project, and the Agile board within that
   project (skipping the board prompt when the project has exactly one visible
   board) — but not for the token.
2. **Given** the user has provided valid YouTrack details and the token
   environment variable is set, **When** the program verifies the connection,
   **Then** it confirms success, saves the non-token settings inside the working
   folder, and proceeds to produce the deck.
3. **Given** the user has provided invalid project/URL or the token environment
   variable is missing, unreachable, or rejected, **When** the program tries to
   verify the connection, **Then** it shows a clear error (including how to set
   the token environment variable when that is the cause), does not save the
   settings, and re-prompts or aborts as appropriate.
4. **Given** saved settings already exist in the folder and the token environment
   variable is set, **When** the program is launched again, **Then** it does not
   re-prompt for URL/project/board and goes straight to producing the deck.

---

### User Story 3 - Pick a different sprint than the most-recent one (Priority: P3)

Sometimes the user wants to recap a sprint other than the latest one
— for example, to redo a deck after fixing data in YouTrack, or to produce a deck
for a colleague's sprint. The program offers a way to choose which sprint to use
instead of always defaulting to the latest-by-end-date sprint.

**Why this priority**: A real but secondary need. The default (latest-by-end-date
sprint on the configured board) covers the common monthly case; explicit sprint
selection is a refinement.

**Independent Test**: With several closed sprints on the configured board, launch
the program in a way that asks for a sprint, choose a non-default sprint, and
confirm the produced deck reflects that sprint's dates and stories.

**Acceptance Scenarios**:

1. **Given** the configured board has more than one closed sprint, **When** the
   user opts to choose a sprint (e.g., via a "pick another sprint" prompt), **Then**
   the program lists the available sprints with their dates and lets the user pick
   one.
2. **Given** the user picks a specific sprint, **When** the deck is produced,
   **Then** the dates and stories in the deck come from that picked sprint and not
   the default one.

---

### Edge Cases

- The working folder contains no pptx template → program asks the user to point at
  one (or to drop one into the folder and retry); it does not invent a template.
- The working folder contains more than one pptx file → program asks the user which
  one is the template before doing anything.
- The configured board has no closed sprints yet → program reports this clearly
  and offers to pick an active sprint or cancel; it does not produce a deck with
  guessed data.
- The configured project has no Agile boards visible to the token → program
  reports this clearly during first-time setup and aborts; settings are not
  saved.
- The selected sprint has zero user stories → program still produces a deck; the
  Finished and Open lists are shown as empty rather than omitted.
- A user story has no title or has unusual characters → it is included in the deck
  using whatever YouTrack returns; the program does not silently drop entries.
- A YouTrack story has no `resolved` value (or the field is missing) → it is
  treated as Open; the program does not attempt to second-guess from the state's
  display name.
- A subtask is in the sprint but its parent is not → the subtask is treated as
  a top-level item and appears on the agenda (FR-019).
- YouTrack is unreachable, times out, or rejects the saved token → program reports
  the error, does not produce a partial deck, and does not overwrite a previous
  good output.
- The user cancels at any prompt → no files are written or modified.
- The program is launched from a folder where it has no permission to write →
  program reports the error before doing any work.
- A required placeholder token (`{{SPRINT_START}}`, `{{SPRINT_END}}`,
  `{{AGENDA_FINISHED}}`, or `{{AGENDA_OPEN}}`) is missing from the template →
  program reports a clear error naming the missing token(s), does not produce
  a partial deck, and does not overwrite an existing good output. The
  `{{RECAP_DATE}}` token is optional; its absence is not an error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The program MUST treat the folder it is launched from as its working
  folder for both inputs (template, saved settings) and outputs (the produced deck).
- **FR-002**: The program MUST locate a pptx template in the working folder. If no
  pptx is present it MUST prompt the user to specify one. If multiple pptx files are
  present it MUST prompt the user to choose the template.
- **FR-003**: The program MUST produce the recap deck as a new pptx file written
  into the working folder, using the filename pattern
  `<template-stem>_<sprint-name>_<sprint-end-YYYY-MM-DD>.pptx`, where
  `<template-stem>` is the template's filename without its `.pptx` extension,
  `<sprint-name>` is the sprint's human-readable name with filesystem-unsafe
  characters replaced safely, and `<sprint-end-YYYY-MM-DD>` is the sprint's end
  date in ISO format. The program MUST NOT modify the original template. The
  pattern MUST be deterministic so a re-run for the same sprint produces the
  same filename and therefore triggers the overwrite prompt in FR-004.
- **FR-004**: When the intended output filename already exists, the program MUST
  prompt the user before overwriting and offer at minimum the choices: overwrite,
  save under a different name, or cancel.
- **FR-005**: The program MUST connect to a YouTrack instance using a
  user-supplied URL, a user-supplied project, and a user-supplied Agile board
  within that project (the board owns the sprints). Where the project has
  exactly one Agile board visible to the token, the program MUST default the
  board to that single board without prompting; where the project has more
  than one, the program MUST prompt the user to choose. The access token is
  sourced from the `YOUTRACK_TOKEN` environment variable. The program MUST
  verify the connection — URL reachable, project visible, board visible —
  before saving the non-token settings.
- **FR-006**: The program MUST persist non-token YouTrack connection settings
  (URL, project, board, last-used sprint reference, and the issue-type filter
  list per FR-018) inside the working folder so that subsequent runs do not
  re-prompt for them. The access token MUST NOT be persisted to disk by the
  program.
- **FR-007**: The program MUST default to recapping the sprint with the latest
  end date on the configured board (regardless of YouTrack's `archived` flag,
  which teams do not always set when a sprint ends), and MUST allow the user to
  choose a different sprint on demand.
- **FR-008**: The program MUST retrieve, for the selected sprint: the sprint's
  human-readable name, its start and end dates, and the full list of issues
  belonging to it together with each issue's ID, title, type, parent reference
  (for FR-019), `resolved` timestamp (used both to drive the Finished/Open
  split in FR-010 and to sort the Finished list per FR-020), and created
  timestamp (used to sort the Open list per FR-020). The retrieved list MUST
  then be filtered to the issue types configured under FR-018 before
  population.
- **FR-009**: The program MUST replace date placeholders in the template with the
  selected sprint's start date and end date. Date placeholders are recognized by
  named text tokens inside the template's text frames: `{{SPRINT_START}}` is
  replaced with the sprint's start date, `{{SPRINT_END}}` with the sprint's end
  date, and `{{RECAP_DATE}}` (the "recap meeting date" placeholder, if present)
  is also filled with the sprint's end date. There is no distinct meeting-date
  concept and the program MUST NOT prompt the user for a separate meeting date.
  Token recognition MUST be exact-match on the literal token strings; the program
  MUST NOT attempt fuzzy matching, regex inference, or shape-name conventions.
  Each substituted date MUST be rendered in long-form English: day of month with
  no leading zero, full English month name, four-digit year, separated by single
  spaces (e.g., `6 May 2026`, `12 December 2026`). The filename pattern in
  FR-003 is unaffected and continues to use ISO `YYYY-MM-DD`.
- **FR-010**: The program MUST populate the agenda slide of the deck with two
  groups of entries: issues whose YouTrack `resolved` attribute is set are shown
  under "Finished", and all other sprint issues are shown under "Open"; the
  user-visible labels match the template's existing labels where present. The
  classification MUST NOT depend on the state's display name (e.g., "Done",
  "Closed", "Completed"). Each entry on the slide MUST display the issue's
  title only — the YouTrack issue ID MUST NOT appear on the slide. The issue
  ID MUST still be recorded in the per-run log (FR-017) so the user can
  cross-reference back to YouTrack. The two agenda regions are identified in
  the template by the named text tokens `{{AGENDA_FINISHED}}` and
  `{{AGENDA_OPEN}}`: each token MUST appear inside a text frame, and the
  program replaces the token with the corresponding list of issue titles
  (one entry per line/bullet within that text frame). The program produces a
  single agenda slide; visual fit of the rendered lists is delegated to the
  autofit behaviour of the template's text frames containing those tokens.
  The program MUST NOT duplicate the agenda slide, cap entries, or otherwise
  alter the list to make it fit. The per-run log (FR-017) captures the entry
  counts so the user can judge whether manual splitting is needed.
- **FR-011**: The program MUST list every issue from the sprint that matches the
  configured issue-type filter (FR-018) in the agenda slide; it MUST NOT
  silently truncate, deduplicate, or omit entries within the filtered set.
  Issues excluded by the filter are not "silent omissions" because the filter
  is user-controlled and recorded in saved settings.
- **FR-012**: When information needed to fill the deck cannot be inferred from
  the folder, the saved settings, or the YouTrack response, the program MUST
  prompt the user interactively with a clear question, a sensible default
  where one exists, and the option to cancel. The prompt mode MUST be selected
  automatically per launch context: when the standard input is a TTY (typical
  of launching from a terminal) the program MUST use console prompts —
  `input()` for free-form text, a numbered list for selection — and when
  standard input is not a TTY (typical of a double-click launch on Windows
  with no console attached) the program MUST use minimal stdlib `tkinter`
  dialogs — text entry, listbox, message box. The detection MUST happen once
  at startup; once chosen, the same mode MUST apply to all prompts for the
  remainder of that run, and the per-run log MUST record which mode was used
  (FR-017).
- **FR-013**: The program MUST never write outside the working folder unless the
  user explicitly confirms a different destination at a prompt.
- **FR-014**: When YouTrack is unreachable or returns an error, the program MUST
  present a clear, plain-language error message, MUST NOT produce a partially
  populated deck, and MUST NOT overwrite an existing good output.
- **FR-015**: The program MUST handle the empty case: a sprint with no stories
  still produces a complete deck whose Finished and Open lists are visibly empty
  rather than missing.
- **FR-016**: The program MUST treat the access token as sensitive: it is read
  from the `YOUTRACK_TOKEN` environment variable, MUST NOT be written to any
  file the program creates (settings, logs, output), and MUST NOT be echoed
  back in plain text in prompts or logs. If `YOUTRACK_TOKEN` is missing or
  empty, the program MUST report this with clear guidance on how to set it
  (naming the variable explicitly) and MUST NOT proceed with a YouTrack call.
- **FR-017**: The program MUST write a per-run log file in the working folder
  named `<output-stem>.log` (where `<output-stem>` is the same stem as the deck
  produced under FR-003) and MUST stream the same content to the console while
  running. The log MUST capture, at minimum: the working folder, the chosen
  template path, the YouTrack URL, project, and board (but never the token),
  the selected sprint identifier, the active issue-type filter (FR-018), the
  count of issues retrieved before and after filtering and the Finished/Open
  split, the count of subtasks collapsed under FR-019, the produced output
  filename, the prompt mode chosen at startup per FR-012 (console or
  tkinter), and any errors or user prompts surfaced during the run.
- **FR-018**: The program MUST support a per-folder issue-type filter — a list
  of YouTrack issue type names (e.g., "Story", "Bug", "Task") that determines
  which issues from the sprint appear on the agenda. On first-time setup the
  filter MUST default to the sentinel value "all" (no filtering). The filter
  MUST be persisted with the rest of saved settings (FR-006) and MUST be
  user-editable between runs (e.g., by editing the saved settings file). When
  the filter is "all", the program MUST NOT filter; when the filter is an
  explicit list, the program MUST log both the unfiltered and filtered counts
  per FR-017.
- **FR-019**: The program MUST collapse parent-child relationships on the
  agenda: an issue is shown only if either it has no parent issue, or its
  parent issue is not also a member of the same sprint. Subtasks whose parent
  is in the same sprint MUST be excluded from the agenda; their work is
  represented implicitly by the parent's Finished/Open classification. The
  program MUST log how many subtasks were collapsed for the run.
- **FR-020**: Within each agenda group the program MUST sort entries
  deterministically: the Finished list is sorted ascending by the issue's
  `resolved` timestamp (earliest resolved at top), and the Open list is sorted
  ascending by the issue's created timestamp (earliest created at top). Ties
  MUST be broken by issue ID ascending so re-runs produce identical output.

### Key Entities *(include if feature involves data)*

- **Pptx Template**: the source presentation supplied by the user. Holds slide
  layouts, the agenda slide, and date/text placeholders that the program fills in.
- **Output Deck**: the new pptx the program produces beside the template, with
  dates and the agenda populated; never overwrites the template.
- **Sprint**: a YouTrack sprint with a name, a start date, an end date, and a
  collection of user stories.
- **Sprint Issue**: an item belonging to the sprint, with at minimum an ID, a
  title, a YouTrack issue type, an optional parent issue reference, a
  `resolved` timestamp (or null/unset if open), and a created timestamp.
  Resolved issues are shown as Finished; unresolved issues are shown as Open.
  Whether a given issue appears on the agenda at all depends on the issue-type
  filter (FR-018) and the subtask-collapse rule (FR-019); within each group,
  ordering is governed by FR-020.
- **Saved Settings**: the per-folder record of the YouTrack URL, project,
  Agile board, last-used sprint reference, and the issue-type filter
  (FR-018), persisted between runs. The access token is not part of saved
  settings; it is read from the `YOUTRACK_TOKEN` environment variable on
  every run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From launching the program to having a usable recap deck on disk
  takes under 1 minute on the routine monthly run, with no manual data entry into
  the deck during that time.
- **SC-002**: 100% of dates and 100% of user-story entries in the produced deck
  match the source sprint in YouTrack, verified by spot-checking against the sprint
  view.
- **SC-003**: First-time setup of the YouTrack connection in a fresh folder
  completes in under 3 minutes, including entering the URL, token, and project.
- **SC-004**: On the second and subsequent runs in a configured folder, the user
  is asked at most one question (sprint selection, only if not defaulted) before
  the deck is produced.
- **SC-005**: The user's manual time spent on the monthly recap deck drops from
  the prior workflow to no more than 2 minutes of cosmetic touch-up after the
  program runs.
- **SC-006**: Zero original template files are modified across runs (the template
  is treated as read-only).
- **SC-007**: When YouTrack data or input is missing, the user always sees an
  explicit prompt or error rather than a silently wrong or partial deck — no
  occurrences of unannounced fallback behaviour are acceptable.

## Assumptions

- The pptx template lives in the same folder as the program at run time. The user
  is responsible for placing it there; the program does not search outside the
  folder.
- The template carries named text tokens — `{{SPRINT_START}}`, `{{SPRINT_END}}`,
  optionally `{{RECAP_DATE}}`, `{{AGENDA_FINISHED}}`, and `{{AGENDA_OPEN}}` —
  inside ordinary text frames at the locations the user wants those values
  rendered. The user is responsible for inserting the tokens into their
  template once; the program does not modify slide layouts, masters, or shape
  names, and does not offer interactive placeholder mapping.
- "Finished" maps to YouTrack's built-in `resolved` attribute on each issue
  (true → Finished); "Open" covers every other in-sprint story. This works
  uniformly across customized workflows because YouTrack maintains the
  `resolved` flag based on per-project state configuration, so no first-time
  mapping prompt is required.
- The YouTrack instance is reachable from the user's machine over the network the
  user normally uses, and the user has an API token with read access to the
  project's sprints and issues. The token is supplied to the program via the
  `YOUTRACK_TOKEN` environment variable rather than stored alongside the folder.
- Non-token settings are stored per-folder, not globally, so that the folder
  remains self-contained and movable between machines (subject to the user
  setting `YOUTRACK_TOKEN` on each machine).
- "Sprint" in the user's YouTrack project is represented either as a YouTrack
  Agile sprint or as an equivalent sprint-like grouping; the program reads
  whichever the project uses.
- Output filenames are derived deterministically from the template name and the
  sprint, so re-runs produce the same name and trigger the overwrite prompt
  rather than silently piling up files.
- The user is on a current desktop OS where a Python-installed `.py` file (or
  thin launcher) is double-clickable, per the project constitution.
