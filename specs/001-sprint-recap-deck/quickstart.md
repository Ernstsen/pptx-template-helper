# Quickstart: Sprint Recap Deck Generator

This is the human-facing "how do I run it from a clean checkout" guide
that the implementation must keep accurate. It is also the
verification recipe the user will follow at every iteration boundary
per Constitution Principle I.

## Prerequisites

- Python 3.11 or later, available on `PATH`.
- A YouTrack instance you can reach over the network.
- A YouTrack API token with read access to the project's sprints and
  issues.
- A pptx template containing the five tokens from
  `contracts/template-tokens.md`.

## One-time setup (per machine, per project clone)

```bash
# from the repository root
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Set the token in your shell or your OS environment:

```bash
# bash / zsh
export YOUTRACK_TOKEN="perm:..."

# Windows PowerShell
$env:YOUTRACK_TOKEN = "perm:..."

# Windows cmd
set YOUTRACK_TOKEN=perm:...
```

The program reads `YOUTRACK_TOKEN` afresh on every run. The token is
never written to disk by the program (FR-016).

## Routine monthly run

1. Drop `sprint_recap.py` (or a shortcut to it) into the working
   folder that holds your pptx template.
2. Make sure `YOUTRACK_TOKEN` is set in that shell/session.
3. Double-click `sprint_recap.py` (Windows) or run
   `python sprint_recap.py` from inside the working folder.
4. On a configured folder, the program goes straight to producing the
   deck for the sprint with the latest end date on the configured
   board. On a fresh folder, it
   first walks you through the YouTrack URL / project / board prompt
   sequence and saves your answers in `sprint-recap.json`.
5. The new deck appears in the same folder as
   `<template-stem>_<sprint-name>_<sprint-end-YYYY-MM-DD>.pptx`,
   accompanied by `<output-stem>.log`. The original template is
   untouched.

## Picking a different sprint (US3)

Run with the `--pick-sprint` flag (or answer "yes" at the optional
"recap a different sprint?" prompt — the exact UX is finalized in
implementation):

```bash
python sprint_recap.py --pick-sprint
```

The program lists all sprints from the configured board with their
dates and lets you pick one.

## Manual verification at iteration handoffs

At the end of each iteration the agent stops and hands off; the user
verifies. The minimum verification recipe per iteration:

1. Run the program from a working folder containing a known template
   and a YouTrack instance with a known sprint.
2. Open the produced deck and confirm the dates and the agenda match
   the sprint.
3. Open the produced log and confirm:
   - it does NOT contain the token,
   - the issue counts match the sprint,
   - the prompt mode line is present,
   - the cross-reference list of `id_readable | bucket | title`
     covers every issue you can see in the deck.
4. Confirm the original template's modification time is unchanged.

## Test suite

```bash
pytest
```

Unit tests cover the deterministic pure-function pieces — date
formatting, classification, sort, subtask collapse, filename
sanitization, and a token-substitution smoke test against
`tests/fixtures/template.pptx` (research §R10).

## Common errors

| What you see | What to do |
|---|---|
| `YOUTRACK_TOKEN not set — see README.md` | Set the env var (see above) and re-run. |
| `Could not reach YouTrack at <url>` | Check VPN / DNS / URL typo. |
| `Token rejected — check YOUTRACK_TOKEN` | Token expired or lacks read access; regenerate in YouTrack. |
| `Project not visible to this token` | The token's user has no access; ask an admin. |
| `Required template tokens missing: {{AGENDA_FINISHED}}` | Edit the template to insert the missing tokens (see `contracts/template-tokens.md`). |
| `Output file already exists — overwrite?` | Pick overwrite, save-as, or cancel — nothing is written until you answer (FR-004). |
