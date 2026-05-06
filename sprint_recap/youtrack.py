"""YouTrack REST client (read-only) per contracts/youtrack-api.md.

The single seam for unit tests is the `http_get` callable: a
`(url, headers) -> (status, body_bytes)` function. The default
implementation wraps `urllib.request`. Tests pass a stub instead.

Error mapping matches the table in contracts/youtrack-api.md.
URL hygiene: trim trailing slash, reject non-http(s) (research §R2a).
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sprint_recap.models import Sprint, SprintIssue

_log = logging.getLogger(__name__)

HttpGet = Callable[[str, dict[str, str]], tuple[int, bytes]]


def _default_http_get(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        # HTTPError is a subclass of URLError. Caller distinguishes by status.
        body = e.read() if hasattr(e, "read") else b""
        return e.code, body


class YouTrackError(Exception):
    """User-facing YouTrack error. Message is safe to surface as-is."""


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    short_name: str


@dataclass(frozen=True)
class Board:
    id: str
    name: str
    project_ids: list[str]
    sprints: list[Sprint]


def _validate_base_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise YouTrackError(f"YouTrack URL must use http(s): {url!r}")
    if not parsed.netloc:
        raise YouTrackError(f"YouTrack URL is missing a host: {url!r}")
    return url.rstrip("/")


def _epoch_ms_to_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


def _epoch_ms_to_date(value: Any):
    dt = _epoch_ms_to_dt(value)
    return dt.date() if dt else None


def _decode_json(body: bytes, url: str) -> Any:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as e:
        raise YouTrackError(
            "Unexpected response from YouTrack — is the URL pointing at the YouTrack API?"
        ) from e
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise YouTrackError(
            "Unexpected response from YouTrack — is the URL pointing at the YouTrack API?"
        ) from e


def _short_body(body: bytes) -> str:
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        return "<binary>"
    text = text.strip()
    return text if len(text) <= 200 else text[:197] + "..."


def _map_error(status: int, body: bytes, url: str, *, what: str) -> YouTrackError:
    if status in (401, 403):
        return YouTrackError("Token rejected — check YOUTRACK_TOKEN")
    if status == 404:
        if "/admin/projects" in url:
            return YouTrackError("Project not visible to this token")
        if "/agiles" in url:
            return YouTrackError("Board not visible to this token")
        return YouTrackError(f"YouTrack returned 404 for {what}")
    if 400 <= status < 500:
        return YouTrackError(
            f"YouTrack rejected the request: {status} — {_short_body(body)}"
        )
    if 500 <= status < 600:
        return YouTrackError(f"YouTrack server error {status} — try again later")
    return YouTrackError(f"YouTrack returned unexpected status {status}")


class YouTrackClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        http_get: HttpGet = _default_http_get,
    ) -> None:
        self.base_url = _validate_base_url(base_url)
        self._token = token
        self._http_get = http_get

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict[str, str], what: str) -> Any:
        query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        url = f"{self.base_url}/api/{path}?{query}"
        try:
            status, body = self._http_get(url, self._headers())
        except urllib.error.URLError as e:
            raise YouTrackError(f"Could not reach YouTrack at {self.base_url}") from e
        if not (200 <= status < 300):
            raise _map_error(status, body, url, what=what)
        return _decode_json(body, url)

    # --- Endpoints ---

    def verify_project(self, query: str) -> list[Project]:
        """Return all projects matching `query` (short name or full name)."""
        data = self._get(
            "admin/projects",
            {"fields": "id,name,shortName", "query": query},
            what="project lookup",
        )
        out: list[Project] = []
        for item in data or []:
            out.append(
                Project(
                    id=str(item.get("id", "")),
                    name=str(item.get("name", "")),
                    short_name=str(item.get("shortName", "")),
                )
            )
        return out

    def list_agile_boards(self) -> list[Board]:
        """List all visible agile boards with their sprints inlined
        (avoids a second round-trip per FR-007 / US3)."""
        data = self._get(
            "agiles",
            {
                "fields": (
                    "id,name,projects(id,shortName),"
                    "sprints(id,name,start,finish,archived)"
                ),
                "$top": "100",
            },
            what="agile boards",
        )
        boards: list[Board] = []
        for raw_board in data or []:
            sprints: list[Sprint] = []
            for raw_sprint in raw_board.get("sprints") or []:
                start = _epoch_ms_to_date(raw_sprint.get("start"))
                end = _epoch_ms_to_date(raw_sprint.get("finish"))
                if start is None or end is None:
                    # Skip sprints lacking dates; they would crash filename
                    # construction and the long-form date renderer.
                    continue
                sprints.append(
                    Sprint(
                        id=str(raw_sprint.get("id", "")),
                        name=str(raw_sprint.get("name", "")),
                        start=start,
                        end=end,
                        archived=bool(raw_sprint.get("archived", False)),
                    )
                )
            boards.append(
                Board(
                    id=str(raw_board.get("id", "")),
                    name=str(raw_board.get("name", "")),
                    project_ids=[
                        str(p.get("id", "")) for p in raw_board.get("projects") or []
                    ],
                    sprints=sprints,
                )
            )
        return boards

    def fetch_sprint_issues(
        self,
        board_id: str,
        sprint_id: str,
    ) -> list[SprintIssue]:
        data = self._get(
            f"agiles/{board_id}/sprints/{sprint_id}",
            {
                "fields": (
                    "issues(idReadable,summary,resolved,created,"
                    "parent(issues(idReadable)),"
                    "customFields(name,value(name)))"
                ),
            },
            what="sprint issues",
        )
        raw_issues = (data or {}).get("issues") or []
        issues: list[SprintIssue] = []
        for raw in raw_issues:
            issue_type = "(unknown)"
            for cf in raw.get("customFields") or []:
                if cf.get("name") == "Type":
                    value = cf.get("value")
                    if isinstance(value, dict):
                        name = value.get("name")
                        if isinstance(name, str) and name:
                            issue_type = name
                    break

            parent_id: Optional[str] = None
            parent = raw.get("parent")
            if isinstance(parent, dict):
                parent_issues = parent.get("issues") or []
                if parent_issues:
                    parent_id = parent_issues[0].get("idReadable")

            created_dt = _epoch_ms_to_dt(raw.get("created"))
            if created_dt is None:
                # `created` is always present per the API; treat absence as 0.
                created_dt = datetime.fromtimestamp(0, tz=timezone.utc)

            issues.append(
                SprintIssue(
                    id_readable=str(raw.get("idReadable", "")),
                    title=str(raw.get("summary", "")),
                    issue_type=issue_type,
                    parent_id_readable=parent_id,
                    resolved_at=_epoch_ms_to_dt(raw.get("resolved")),
                    created_at=created_dt,
                )
            )
        if len(issues) >= 1000:
            _log.warning(
                "fetch_sprint_issues: hit $top=1000 cap; future paging may be required"
            )
        return issues
