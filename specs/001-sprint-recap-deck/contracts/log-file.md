# Contract: per-run log file (`<output-stem>.log`)

**Location**: same folder as the produced deck (the working folder).
**Filename**: `<output-stem>.log`, where `<output-stem>` is the deck's
filename without its `.pptx` extension. Identical stem on a re-run for
the same sprint, so the log file is overwritten alongside the deck
(FR-003 / FR-004 govern the deck overwrite prompt; the matching log
file is overwritten in lockstep with whatever choice the user made for
the deck).

**Encoding**: UTF-8, plain text, line-oriented. Same content is also
streamed to stdout as the program runs (FR-017).

## Format

Each line is `YYYY-MM-DD HH:MM:SS LEVEL message`. Levels used:

- `INFO` — normal progress.
- `WARN` — non-fatal anomalies (e.g. `issue_type_filter: []` treated
  as `"all"`).
- `ERROR` — what was reported to the user before aborting.

## Required content (FR-017)

The log MUST contain, at a minimum, lines covering:

1. **Run header** — start timestamp, working folder absolute path,
   chosen template path, prompt mode (`prompt_mode=console` or
   `prompt_mode=tkinter`).
2. **YouTrack target** — base URL, project short name, board name,
   board id. **The token MUST NOT appear** (FR-016, research §R7).
3. **Sprint selection** — sprint id, sprint name, start date (ISO),
   end date (ISO).
4. **Issue retrieval** — total issues retrieved from YouTrack
   (`unfiltered_count`).
5. **Filter application** — the active `issue_type_filter` value
   (verbatim, e.g. `"all"` or `["Story", "Bug"]`), and the
   `filtered_count` after filtering.
6. **Subtask collapse** — `collapsed_subtask_count` per FR-019.
7. **Final split** — `finished_count`, `open_count`. Constraint:
   `finished_count + open_count == filtered_count - collapsed_subtask_count`.
8. **Cross-reference list** — every issue actually placed on the deck,
   one line per issue, formatted as
   `id_readable | bucket | title` so the user can cross-reference
   back to YouTrack (FR-010 — IDs are not on the slide but are in the
   log).
9. **Output filename** — final pptx path written.
10. **Prompts surfaced** — every interactive prompt the user saw and
    the answer they chose.
11. **Errors** — any error message that was shown to the user before
    abort.
12. **Run footer** — end timestamp; success / error.

## Forbidden content

- The `YOUTRACK_TOKEN` value.
- Full HTTP request headers (the bearer header would leak the token).
- Stack traces from third-party libraries unless they are part of an
  ERROR line that the user already saw — and even then the line is
  paraphrased to remove credential-bearing context (research §R7).

## Sample (illustrative)

```text
2026-05-06 10:14:02 INFO  ── sprint-recap run start ──
2026-05-06 10:14:02 INFO  working_folder = /home/jane/ramboll-recap
2026-05-06 10:14:02 INFO  template = /home/jane/ramboll-recap/Recap-Template.pptx
2026-05-06 10:14:02 INFO  prompt_mode = console
2026-05-06 10:14:02 INFO  youtrack_url = https://yt.example.com
2026-05-06 10:14:02 INFO  project = PROJ (id=0-7)
2026-05-06 10:14:02 INFO  board = PROJ Scrum (id=121-3)
2026-05-06 10:14:03 INFO  sprint = Sprint 42 (id=121-318) 2026-04-08 → 2026-05-05
2026-05-06 10:14:04 INFO  issues_retrieved = 17
2026-05-06 10:14:04 INFO  issue_type_filter = "all"
2026-05-06 10:14:04 INFO  filtered_count = 17
2026-05-06 10:14:04 INFO  collapsed_subtasks = 3
2026-05-06 10:14:04 INFO  finished_count = 9   open_count = 5
2026-05-06 10:14:04 INFO  agenda:
2026-05-06 10:14:04 INFO    PROJ-301 | finished | Migrate billing service to v3
2026-05-06 10:14:04 INFO    PROJ-310 | finished | Hot-patch invoice rounding
2026-05-06 10:14:04 INFO    ...
2026-05-06 10:14:04 INFO    PROJ-355 | open     | Investigate p99 latency on report API
2026-05-06 10:14:05 INFO  output = /home/jane/ramboll-recap/Recap-Template_Sprint-42_2026-05-05.pptx
2026-05-06 10:14:05 INFO  ── sprint-recap run end (success) ──
```
