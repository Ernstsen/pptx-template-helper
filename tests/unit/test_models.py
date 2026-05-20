"""Spec 005 — `AgendaRow` per-bucket display wrapper.

Covers `AgendaRow.from_issue` initialization and the proxy properties
(`id_readable`, `is_finished`) that let renderer and categorization code
treat a row like a thin wrapper around its `SprintIssue`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sprint_recap.models import AgendaRow, SprintIssue


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def _issue(
    id_readable: str = "PROJ-1",
    title: str = "Original title",
    *,
    resolved: datetime | None = None,
) -> SprintIssue:
    return SprintIssue(
        id_readable=id_readable,
        title=title,
        issue_type="Story",
        parent_id_readable=None,
        resolved_at=resolved,
        created_at=_utc(2026, 4, 1),
    )


def test_agenda_row_from_issue_initializes_display_title_to_issue_title() -> None:
    issue = _issue(title="Migrate billing service to v3")
    row = AgendaRow.from_issue(issue)
    assert row.issue is issue
    assert row.display_title == "Migrate billing service to v3"


def test_agenda_row_display_title_is_independent_of_issue_title() -> None:
    """Editing `display_title` must not mutate the wrapped (frozen) issue."""
    issue = _issue(title="Original")
    row = AgendaRow.from_issue(issue)
    row.display_title = "Edited"
    assert row.display_title == "Edited"
    assert row.issue.title == "Original"


def test_agenda_row_id_readable_proxies_through() -> None:
    row = AgendaRow.from_issue(_issue(id_readable="PROJ-42"))
    assert row.id_readable == "PROJ-42"


def test_agenda_row_is_finished_true_when_issue_resolved() -> None:
    row = AgendaRow.from_issue(_issue(resolved=_utc(2026, 5, 1)))
    assert row.is_finished is True


def test_agenda_row_is_finished_false_when_issue_unresolved() -> None:
    row = AgendaRow.from_issue(_issue(resolved=None))
    assert row.is_finished is False
