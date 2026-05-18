# sprint-recap

A small Python desktop tool that turns a YouTrack sprint into a populated
pptx recap deck. Drop `sprint_recap.py` into a folder containing your
template, set `YOUTRACK_TOKEN`, double-click, and a fresh deck appears
beside the template with the dates and agenda filled in.

See `specs/001-sprint-recap-deck/` for the full specification, plan,
contracts, and quickstart.

## Prerequisites

- Python 3.11 or later, available on `PATH`.
- A YouTrack instance you can reach over the network.
- A YouTrack API token with read access to the project's sprints and
  issues.
- A pptx template containing the required tokens listed below.

## Template tokens

Place these tokens inside text frames on your template slides. The
program finds them by exact string match and replaces them when
generating the deck.

### Date tokens (in-place replacement)

These are replaced inside the paragraph they appear in — surrounding
text is preserved. The substituted value uses long-form English dates
with no leading zero on the day (e.g. `6 May 2026`).

| Token | Replaced with | Required? |
|---|---|---|
| `{{SPRINT_START}}` | Sprint start date | Yes (may appear more than once) |
| `{{SPRINT_END}}` | Sprint end date | Yes (may appear more than once) |
| `{{RECAP_DATE}}` | Recap-meeting date (same as sprint end) | No |

### Agenda tokens (full text-frame replacement)

Each agenda token must be the **sole content** of its text frame (e.g.
an empty bullet text box). The program clears the frame and writes one
paragraph per issue title. The first paragraph inherits the formatting
of the original first run so your bullet style carries over.

Each agenda token must appear **exactly once**; duplicates cause an
error.

| Token | Replaced with | Required? |
|---|---|---|
| `{{AGENDA_DEMO}}` | Titles of resolved issues marked for demo | Yes |
| `{{AGENDA_NO_DEMO}}` | Titles of resolved issues not marked for demo | Yes |
| `{{AGENDA_OPEN}}` | Titles of unresolved issues | Yes |

### Demo-item slide expansion (speaker notes)

These tags go in **speaker notes**, not on the slide body. They mark a
range of template slides that gets cloned once per demo issue.

| Token | Placement | Purpose |
|---|---|---|
| `{{DEMO_ITEM_START}}` | Speaker notes of the first slide in the range | Marks the start of the per-demo-item template |
| `{{DEMO_ITEM_END}}` | Speaker notes of the last slide in the range | Marks the end of the per-demo-item template |
| `{{ITEM_TITLE}}` | Slide body, within the demo-item range | Replaced with the demo issue's title on each cloned slide |

The start/end pair is optional — if absent, no slide expansion occurs.
When present, each tag must appear exactly once and the start must
precede the end. The tags are stripped from speaker notes on the
generated slides.

## One-time setup

```bash
# from the repository root
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Setting `YOUTRACK_TOKEN`

The program reads `YOUTRACK_TOKEN` afresh on every run. It is never
written to settings, logs, or the produced deck (FR-016).

### bash / zsh (macOS, Linux, WSL)

```bash
export YOUTRACK_TOKEN="perm:..."
```

### Windows PowerShell

```powershell
$env:YOUTRACK_TOKEN = "perm:..."
```

### Windows cmd

```cmd
set YOUTRACK_TOKEN=perm:...
```

To make the variable persist across sessions on Windows, set it via
**System Properties → Environment Variables**.

## Routine monthly run

1. Drop `sprint_recap.py` (or a shortcut to it) into the working folder
   that holds your pptx template.
2. Make sure `YOUTRACK_TOKEN` is set in that shell/session.
3. Double-click `sprint_recap.py` (Windows) or run
   `python sprint_recap.py` from inside the working folder.
4. On a configured folder, the program goes straight to producing the
   deck for the sprint with the latest end date on the configured
   board. On a fresh folder (no `sprint-recap.json`), it walks you
   through prompts for YouTrack URL, project, and (only when the
   project has more than one visible board) board, then saves the
   non-token settings to `sprint-recap.json` and proceeds to produce
   the deck. The token is read from `YOUTRACK_TOKEN` and is never
   saved (FR-016).
5. The new deck appears as
   `<template-stem>_<sprint-name>_<sprint-end-YYYY-MM-DD>.pptx`,
   accompanied by `<output-stem>.log`. The original template is
   untouched.

## Editing the issue-type filter

The agenda defaults to **every** issue in the sprint. To narrow the deck
to specific YouTrack issue types (e.g. only `Story` and `Bug`), hand-edit
the `issue_type_filter` field of `sprint-recap.json` between runs (FR-018).

```jsonc
{
  // ...
  "issue_type_filter": "all"            // default — no filtering
}
```

```jsonc
{
  // ...
  "issue_type_filter": ["Story", "Bug"] // only these types appear on the agenda
}
```

Rules:

- **Default `"all"`** means no filtering: every retrieved issue is
  classified Finished/Open and placed on the agenda.
- **Array of strings** is an inclusion list compared case-insensitively
  against each issue's `Type` custom field. Issues with a non-matching
  `Type` are dropped before the Finished/Open split (and so are absent
  from the cross-reference list in the log).
- **Empty array `[]`** is treated as `"all"` and a `WARN` line is
  written to the per-run log so the change is auditable. Use `"all"`
  explicitly if that's what you want.
- The filter does not affect FR-019 subtask collapse: a parent that is
  filtered out still suppresses its in-sprint children only via the
  collapse rule (`is_subtask_to_collapse`), not via the filter.

The filter is the only field of `sprint-recap.json` you should hand-edit
between runs. All other fields are program-managed.

## Building a standalone binary

You can package the tool as a single executable so end-users don't need
Python installed. The repo includes build scripts for both platforms.

### Windows

Double-click `build.bat` (or run it from cmd). It creates a temporary
venv, installs dependencies plus PyInstaller, and produces
`dist\sprint_recap.exe`. Copy the exe next to your pptx template.

```cmd
build.bat
```

### Linux

Run `build.sh` from the repo root with the venv active:

```bash
source venv/bin/activate
bash build.sh
```

The binary lands at `dist/sprint_recap`. Copy it next to your pptx
template.

### Notes

- Python 3.11+ is required on the **build** machine only. The resulting
  binary has no Python dependency.
- PyInstaller is a build-time dependency and is not listed in
  `requirements.txt`. The build scripts install it automatically.
- The `--windowed` flag suppresses the console window on Windows
  (double-click friendly). On Linux it is harmless.
- `YOUTRACK_TOKEN` must still be set in the environment where the binary
  runs — the exe reads it at startup just like the script.

## Tests

```bash
pytest
```

## Common errors

| What you see | What to do |
|---|---|
| `YOUTRACK_TOKEN not set — see README.md` | Set the env var (above) and re-run. Console users see a stderr line; double-click users see a dialog box. No `sprint-recap.json` is written. |
| `YouTrack URL must use http(s) and have a host: ...` | Re-enter the URL during first-time setup; include `https://` and the host. |
| `Could not reach YouTrack at <url>` | Check VPN / DNS / URL typo. No settings file is written if this happens during first-time setup. |
| `Token rejected — check YOUTRACK_TOKEN` | Token expired or lacks read access; regenerate in YouTrack. No settings file is written if this happens during first-time setup. |
| `Project not visible to this token` | The token's user has no access; ask an admin. During first-time setup, you can also re-enter a different project name. |
| `No Agile boards visible for project ...` | The token can see the project but no Agile boards within it; ask an admin to grant Agile board permissions. No settings file is written. |
| `Required template tokens missing: {{AGENDA_FINISHED}}` | Edit the template to insert the missing tokens. |
| `Output file already exists — overwrite?` | Pick overwrite, save-as, or cancel — nothing is written until you answer. |
