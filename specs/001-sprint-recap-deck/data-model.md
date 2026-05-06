# Phase 1 Data Model: Sprint Recap Deck Generator

This file lists the in-memory entities the program manipulates and the rules
they must obey. External representations (settings JSON, log file, pptx
template tokens, YouTrack request/response) are documented in `contracts/`.

## Entities

### `Sprint`

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` | `str` | YouTrack `agiles/.../sprints[].id` | Internal sprint identifier; used in API queries. |
| `name` | `str` | YouTrack `sprints[].name` | Human label (e.g. "Sprint 42"); feeds the filename and the deck. |
| `start` | `datetime.date` | YouTrack `sprints[].start` (epoch ms → date) | Renders into `{{SPRINT_START}}` in long-form English. |
| `end` | `datetime.date` | YouTrack `sprints[].finish` (epoch ms → date) | Renders into `{{SPRINT_END}}` and `{{RECAP_DATE}}`; ISO form drives the filename suffix. |
| `archived` | `bool` | YouTrack `sprints[].archived` | Parsed for completeness; the FR-007 picker ignores it (teams do not always archive finished sprints). |

**Validation**:
- `start` and `end` must be present; otherwise the sprint is excluded from
  pickable lists and a clear error is shown if it was the user's choice.
- `end >= start` is expected; if violated, log a warning and proceed (the
  spec asks us not to second-guess YouTrack data).

### `SprintIssue`

| Field | Type | Source | Notes |
|---|---|---|---|
| `id_readable` | `str` | YouTrack `issues[].idReadable` | e.g. `PROJ-123`; appears only in the per-run log, never on the slide (FR-010). |
| `title` | `str` | YouTrack `issues[].summary` | The text rendered on the agenda slide. |
| `issue_type` | `str` | `customFields[name="Type"].value.name` | Used by the FR-018 issue-type filter; missing/null treated as the literal string `(unknown)` so it can't crash the filter. |
| `parent_id_readable` | `str \| None` | `parent.issues[0].idReadable` (if any) | Drives FR-019 subtask collapse. None = top-level. |
| `resolved_at` | `datetime.datetime \| None` | `issues[].resolved` (epoch ms → UTC datetime) | None = Open; not-None = Finished (FR-010). Drives Finished sort (FR-020). |
| `created_at` | `datetime.datetime` | `issues[].created` (epoch ms → UTC datetime) | Drives Open sort (FR-020). |

**Derived predicates**:
- `is_finished` ≡ `resolved_at is not None`. The classification MUST NOT
  inspect any state-name string (FR-010).
- `is_subtask_to_collapse(self, sprint_ids)` ≡
  `self.parent_id_readable is not None and self.parent_id_readable in sprint_ids`.
  Where `sprint_ids` is the set of `id_readable` values for all issues
  retrieved for the sprint *before* type-filtering. (Subtask collapse is
  computed against the full sprint membership, not against the filtered
  subset, so a Bug-typed parent that is later filtered out still hides its
  subtasks. This matches the spec's "represented implicitly by the parent's
  Finished/Open classification" wording.)

### `IssueTypeFilter`

| Field | Type | Source | Notes |
|---|---|---|---|
| `value` | `Literal["all"] \| list[str]` | Settings file (`sprint-recap.json`) | `"all"` = no filter (default). A list of type names = include only issues whose `issue_type` matches case-insensitively. |

**Validation** (when loaded from disk):
- `"all"` and `list[str]` are the only legal shapes; any other shape →
  treat as corrupt settings, log a clear error, and re-run first-time
  setup rather than guessing.
- Empty list `[]` is treated as `"all"` (an empty filter excluding nothing
  is harmless and avoids a confusing "every issue filtered out" run);
  log a one-line note when this happens.

### `SavedSettings`

The on-disk state per FR-006. The detailed JSON shape is in
`contracts/settings-file.md`; the in-memory dataclass holds:

- `youtrack_url: str` — base URL, no trailing slash, e.g. `https://yt.example.com`.
- `project_id: str` and `project_short_name: str` — both stored so the
  user-facing log shows the short name while API calls use the id.
- `board_id: str` and `board_name: str` — similarly, both kept.
- `last_sprint_id: str | None` — last sprint successfully recapped from
  this folder; informational only.
- `issue_type_filter: IssueTypeFilter` — see above; default `"all"`.

**Token note**: `YOUTRACK_TOKEN` is NEVER a field of `SavedSettings`
(FR-006, FR-016). It is read from the environment at the start of every
run and held only in the YouTrack client.

### `RunInputs`

The transient bundle that the `app.py` orchestrator builds for one run.
Not persisted; not a contract; documented here so the modules don't
share globals.

- `working_folder: pathlib.Path` — the folder the program was launched
  from (per Constitution III).
- `template_path: pathlib.Path` — the chosen pptx template within the
  working folder (FR-002).
- `settings: SavedSettings` — loaded or just-completed.
- `token: str` — from `YOUTRACK_TOKEN`.
- `sprint: Sprint` — the chosen sprint for this run.
- `issues: list[SprintIssue]` — full sprint membership before filtering;
  used both for FR-019 subtask collapse and FR-017 "count before
  filtering".
- `prompt_mode: Literal["console", "tkinter"]` — chosen once (FR-012).
- `output_path: pathlib.Path` — derived from FR-003.
- `log_path: pathlib.Path` — `output_path.with_suffix(".log")`.

### `AgendaPlan`

The final, sorted, filtered, collapsed lists handed to the deck writer.

- `finished: list[SprintIssue]` — sorted ascending by
  `(resolved_at, id_readable)` (FR-020).
- `open: list[SprintIssue]` — sorted ascending by
  `(created_at, id_readable)` (FR-020).
- `unfiltered_count: int` — total sprint issues before the FR-018 filter
  and FR-019 collapse, for FR-017 logging.
- `filtered_count: int` — count after the FR-018 filter, before the
  FR-019 collapse.
- `collapsed_subtask_count: int` — count of subtasks dropped by FR-019.

Invariants:
- `len(finished) + len(open) == filtered_count - collapsed_subtask_count`.
- For every issue `i` in `finished`: `i.resolved_at is not None`.
- For every issue `i` in `open`: `i.resolved_at is None`.
- The two lists are disjoint by id.

## Lifecycle

```text
load SavedSettings (or run first-time setup → save)
└─→ pick Sprint (default = latest by end date; user can pick another)
    └─→ fetch full SprintIssue list
        └─→ apply IssueTypeFilter           → filtered_count
            └─→ apply FR-019 subtask collapse → collapsed_subtask_count
                └─→ classify finished vs open (resolved_at)
                    └─→ sort each per FR-020
                        └─→ build AgendaPlan
                            └─→ render deck + log
```
