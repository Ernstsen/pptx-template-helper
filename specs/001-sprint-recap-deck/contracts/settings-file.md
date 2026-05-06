# Contract: `sprint-recap.json` (saved settings file)

**Location**: in the working folder (the folder the program is launched
from). One file per folder. Created on the first successful first-time
setup (US2). Never created if first-time setup verification fails
(FR-005, FR-014). Never contains `YOUTRACK_TOKEN` (FR-006, FR-016).

**Encoding**: UTF-8, JSON. Written with `json.dump(..., indent=2,
sort_keys=True, ensure_ascii=False)` so the user can hand-edit the
issue-type filter (FR-018).

## Schema (v1)

```json
{
  "schema_version": 1,
  "youtrack_url": "https://youtrack.example.com",
  "project_id": "0-7",
  "project_short_name": "PROJ",
  "board_id": "121-3",
  "board_name": "PROJ Scrum",
  "last_sprint_id": "121-318",
  "issue_type_filter": "all"
}
```

### Field rules

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | integer | yes | Set to `1`. The program rejects unknown versions and re-runs first-time setup with a clear message. |
| `youtrack_url` | string | yes | Base URL; must start with `http://` or `https://`; trailing slash trimmed by the program before saving. |
| `project_id` | string | yes | YouTrack internal id (e.g. `0-7`). Used in API calls. |
| `project_short_name` | string | yes | YouTrack short name (e.g. `PROJ`). Echoed in user-facing log lines. |
| `board_id` | string | yes | YouTrack agile board id. |
| `board_name` | string | yes | Board's display name; used for log lines and user-facing messages (`board = <name> (id=<id>)`). The id, not the name, is what the YouTrack API call uses. |
| `last_sprint_id` | string \| null | no | Informational. Updated after every successful run. |
| `issue_type_filter` | `"all"` \| array of strings | yes | Default `"all"` = no filtering. An array means "include only issues whose `Type` custom field, compared case-insensitively, is in this list". An empty array is treated as `"all"` (with a logged note). |

### Forbidden fields

`YOUTRACK_TOKEN`, `token`, `bearer`, `password`, `api_key` — the program
must reject any field in this set as a corruption / pasted-by-mistake
signal: log a clear warning naming the field, refuse to load, and
ask the user to remove it manually rather than silently dropping it.

## Concurrency / atomicity

The program writes the file by serializing to a sibling
`sprint-recap.json.tmp` and atomically renaming it over
`sprint-recap.json`. This avoids a half-written file if the program is
killed mid-write. Reading is a single `json.load`; if it raises
`JSONDecodeError`, the program treats the folder as un-configured (US2)
rather than guessing.

## User edits between runs

The user is expected to hand-edit `issue_type_filter` between runs to
add/remove issue types (FR-018). All other fields are program-managed.
If the user edits a program-managed field by hand and breaks
verification on the next run, the program re-runs first-time setup
(re-prompting for the broken field).
