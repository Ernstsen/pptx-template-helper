# Contract: YouTrack REST API surface used

The program is intentionally coupled to a small, stable subset of the
YouTrack REST API. This file documents that subset so a future reader
can verify the program against any YouTrack version and so the unit
tests can stub it deterministically.

**Auth**: every request carries
`Authorization: Bearer ${YOUTRACK_TOKEN}` and `Accept: application/json`.
Token sourced from the environment per FR-016.

**Base**: the `youtrack_url` field of `sprint-recap.json` (no trailing
slash). All endpoints below are joined as `<base>/api/<path>`.

## Endpoints used

### 1. Verify project visibility (first-time setup)

```text
GET /api/admin/projects?fields=id,name,shortName&query={user_input}
```

- `query` is whatever the user typed for "project" (short name or full
  name; YouTrack matches both).
- Response: array of project descriptors. Zero results = not visible
  to the token (FR-005 ¶3 error path). One result = candidate. Multiple
  results = the user is prompted to disambiguate via the chosen
  prompt mode (FR-012).

### 2. Enumerate Agile boards for the chosen project

```text
GET /api/agiles
    ?fields=id,name,projects(id,shortName),sprints(id,name,start,finish,archived)
    &$top=100
```

The program fetches all boards visible to the token and filters
client-side to the boards whose `projects` array contains the chosen
`project.id`. This avoids a server-side query parameter that varies
across YouTrack versions.

- 0 boards visible for the project → FR-005 edge case ("no Agile
  boards visible to the token"): clear error during first-time setup,
  abort, settings not saved.
- Exactly 1 board → defaulted (FR-005 ¶2).
- ≥ 2 boards → user is prompted (FR-005 ¶2).

The same response also yields the list of sprints per board, which
covers FR-007's "default to the latest by end date" and US3's "pick
another sprint" without a second round-trip.

### 3. Fetch issues for the selected sprint

```text
GET /api/agiles/{board_id}/sprints/{sprint_id}
    ?fields=issues(idReadable,summary,resolved,created,
                   parent(issues(idReadable)),
                   customFields(name,value(name)))
```

The board id and sprint id are taken from the agile-boards response
above; the program never builds a YouTrack search-query expression for
this call. (An earlier draft used `GET /api/issues?query=Board {board}: {sprint}`;
that was rejected after live testing — the search parser returns HTTP
400 on multi-word board names and the `Board:` attribute filter did
not consistently restrict by board context.)

Response shape — the endpoint returns a Sprint object whose `issues`
array contains the issues for that sprint:

| JSON path | Mapped to | Notes |
|---|---|---|
| `issues[].idReadable` | `SprintIssue.id_readable` | e.g. `PROJ-123`. |
| `issues[].summary` | `SprintIssue.title` | The on-slide text. |
| `issues[].resolved` | `SprintIssue.resolved_at` | Unix epoch ms or null. Null = Open. |
| `issues[].created` | `SprintIssue.created_at` | Unix epoch ms (always present). |
| `issues[].parent.issues[0].idReadable` | `SprintIssue.parent_id_readable` | Absent or empty array = top-level. |
| `issues[].customFields[name="Type"].value.name` | `SprintIssue.issue_type` | Missing → the literal string `(unknown)`. |

The endpoint returns every issue attached to the sprint in one
response; there is no `$top` parameter and paging is not currently
required (typical sprints are well under any practical ceiling).

## Error mapping (research §R2b)

| Condition | User message | Behavior |
|---|---|---|
| `urllib.error.URLError` (DNS / refused / timeout) | "Could not reach YouTrack at `<url>`" | Abort; no deck written. |
| HTTP 401 / 403 | "Token rejected — check `YOUTRACK_TOKEN`" | Abort; do NOT echo the token; do not save settings if in first-time setup. |
| HTTP 404 on project endpoint | "Project not visible to this token" | Re-prompt for project (first-time setup) or abort (subsequent runs). |
| HTTP 404 on agiles endpoint | "Board not visible to this token" | Covers both `/api/agiles` (board lookup) and `/api/agiles/<board>/sprints/<sprint>` (sprint fetch). Re-prompt for board (first-time setup) or abort (subsequent runs). |
| HTTP 4xx other | "YouTrack rejected the request: `<status>` — `<short body>`" | Abort. |
| HTTP 5xx | "YouTrack server error `<status>` — try again later" | Abort. |
| Non-JSON response body | "Unexpected response from YouTrack — is the URL pointing at the YouTrack API?" | Abort. |

Per FR-014, none of these paths produce a partial deck or overwrite an
existing good output.

## What the program does NOT call

- Project/board/sprint *mutation* endpoints. The program is read-only
  against YouTrack.
- The `/api/users` endpoints. The program does not need user identity
  beyond what the token implies.
- WebSocket / event streams.

## Stubbing for tests

Per research §R10, the YouTrack client exposes a single seam — a
`http_get(url, headers) -> (status, body)` callable — that unit tests
can override. The mapping from the URLs above to the
`SprintIssue`/`Sprint` dataclasses is itself unit-tested against a
small set of recorded JSON fixtures stored under
`tests/fixtures/youtrack/`.
