"""Classification + sort + subtask collapse (FR-010, FR-018, FR-019, FR-020)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sprint_recap.classify import build_agenda_plan
from sprint_recap.models import SprintIssue


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def _issue(
    id_readable: str,
    *,
    title: str = "x",
    issue_type: str = "Story",
    parent: str | None = None,
    resolved: datetime | None = None,
    created: datetime | None = None,
) -> SprintIssue:
    return SprintIssue(
        id_readable=id_readable,
        title=title,
        issue_type=issue_type,
        parent_id_readable=parent,
        resolved_at=resolved,
        created_at=created or _utc(2026, 4, 1),
    )


def test_finished_iff_resolved_at_is_not_none() -> None:
    issues = [
        _issue("PROJ-1", resolved=_utc(2026, 4, 10)),
        _issue("PROJ-2", resolved=None),
    ]
    plan = build_agenda_plan(issues, type_filter="all")
    assert [i.id_readable for i in plan.finished] == ["PROJ-1"]
    assert [i.id_readable for i in plan.open] == ["PROJ-2"]


def test_classification_does_not_inspect_state_name_strings() -> None:
    """Even an issue with a state-shaped title should remain Open if not resolved."""
    issues = [
        _issue("PROJ-3", title="Done: ship the thing", resolved=None),
    ]
    plan = build_agenda_plan(issues, type_filter="all")
    assert plan.finished == []
    assert [i.id_readable for i in plan.open] == ["PROJ-3"]


def test_finished_sort_by_resolved_then_id_ascending() -> None:
    issues = [
        _issue("PROJ-2", resolved=_utc(2026, 4, 10, 10)),
        _issue("PROJ-1", resolved=_utc(2026, 4, 10, 9)),
        _issue("PROJ-3", resolved=_utc(2026, 4, 10, 10)),
    ]
    plan = build_agenda_plan(issues, type_filter="all")
    assert [i.id_readable for i in plan.finished] == ["PROJ-1", "PROJ-2", "PROJ-3"]


def test_open_sort_by_created_then_id_ascending() -> None:
    issues = [
        _issue("PROJ-2", created=_utc(2026, 4, 5)),
        _issue("PROJ-1", created=_utc(2026, 4, 6)),
        _issue("PROJ-3", created=_utc(2026, 4, 5)),
    ]
    plan = build_agenda_plan(issues, type_filter="all")
    assert [i.id_readable for i in plan.open] == ["PROJ-2", "PROJ-3", "PROJ-1"]


def test_subtask_collapsed_iff_parent_is_in_sprint() -> None:
    parent = _issue("PROJ-100", resolved=_utc(2026, 4, 10))
    in_sprint_subtask = _issue("PROJ-101", parent="PROJ-100", resolved=_utc(2026, 4, 11))
    out_of_sprint_subtask = _issue("PROJ-102", parent="PROJ-999", resolved=None)
    plan = build_agenda_plan(
        [parent, in_sprint_subtask, out_of_sprint_subtask], type_filter="all"
    )
    finished_ids = [i.id_readable for i in plan.finished]
    open_ids = [i.id_readable for i in plan.open]
    assert "PROJ-101" not in finished_ids  # collapsed under parent
    assert "PROJ-100" in finished_ids
    assert "PROJ-102" in open_ids  # parent not in sprint → kept
    assert plan.collapsed_subtask_count == 1


def test_subtask_collapse_uses_full_pre_filter_membership() -> None:
    """A bug-typed parent that is later filtered out still hides its subtasks
    (data-model.md `is_subtask_to_collapse`)."""
    parent = _issue("PROJ-100", issue_type="Bug", resolved=_utc(2026, 4, 10))
    subtask = _issue("PROJ-101", issue_type="Story", parent="PROJ-100", resolved=None)
    plan = build_agenda_plan([parent, subtask], type_filter=["Story"])
    assert [i.id_readable for i in plan.finished] == []
    assert [i.id_readable for i in plan.open] == []  # subtask collapsed by parent
    assert plan.unfiltered_count == 2
    assert plan.filtered_count == 1  # only Story survives the filter
    assert plan.collapsed_subtask_count == 1


def test_empty_sprint_yields_empty_plans_with_correct_counts() -> None:
    plan = build_agenda_plan([], type_filter="all")
    assert plan.finished == []
    assert plan.open == []
    assert plan.unfiltered_count == 0
    assert plan.filtered_count == 0
    assert plan.collapsed_subtask_count == 0


def test_filter_default_all_is_noop() -> None:
    issues = [
        _issue("PROJ-1", issue_type="Story", resolved=None),
        _issue("PROJ-2", issue_type="Bug", resolved=_utc(2026, 4, 10)),
    ]
    plan = build_agenda_plan(issues, type_filter="all")
    assert plan.unfiltered_count == 2
    assert plan.filtered_count == 2


def test_filter_case_insensitive_match() -> None:
    issues = [
        _issue("PROJ-1", issue_type="Story", resolved=None),
        _issue("PROJ-2", issue_type="bug", resolved=None),
    ]
    plan = build_agenda_plan(issues, type_filter=["BUG"])
    assert [i.id_readable for i in plan.open] == ["PROJ-2"]


def test_empty_list_filter_treated_as_all() -> None:
    """data-model.md IssueTypeFilter rules: empty list → 'all' with logged WARN."""
    issues = [
        _issue("PROJ-1", issue_type="Story", resolved=None),
    ]
    plan = build_agenda_plan(issues, type_filter=[])
    assert [i.id_readable for i in plan.open] == ["PROJ-1"]


def test_invariant_finished_plus_open_equals_filtered_minus_collapsed() -> None:
    parent = _issue("PROJ-100", resolved=_utc(2026, 4, 10))
    sub = _issue("PROJ-101", parent="PROJ-100", resolved=None)
    other = _issue("PROJ-200", resolved=None)
    plan = build_agenda_plan([parent, sub, other], type_filter="all")
    assert (
        len(plan.finished) + len(plan.open)
        == plan.filtered_count - plan.collapsed_subtask_count
    )
