"""Spec 004 — `_apply_categorization` rebuilds the four bucket lists.

Coverage:
- defaults: identity mapping leaves the plan equivalent.
- invariant: a mapping that drops an issue raises ValueError.
- invariant: an unknown bucket raises ValueError.
- in-bucket sort: an open issue elevated to Present sits after the
  finished entries that landed there (finished by resolved_at, then
  unresolved by created_at).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

import logging

from sprint_recap.app import _apply_categorization, _write_cross_reference
from sprint_recap.models import AgendaPlan, AgendaRow, SprintIssue


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def _issue(
    id_readable: str,
    *,
    resolved: datetime | None = None,
    created: datetime | None = None,
) -> SprintIssue:
    return SprintIssue(
        id_readable=id_readable,
        title=id_readable,
        issue_type="Story",
        parent_id_readable=None,
        resolved_at=resolved,
        created_at=created or _utc(2026, 4, 1),
    )


def _default_plan(
    finished: list[SprintIssue], open_: list[SprintIssue]
) -> AgendaPlan:
    return AgendaPlan(
        demo=[],
        no_demo=[AgendaRow.from_issue(i) for i in finished],
        open=[AgendaRow.from_issue(i) for i in open_],
        excluded=[],
        unfiltered_count=len(finished) + len(open_),
        filtered_count=len(finished) + len(open_),
        collapsed_subtask_count=0,
    )


# ---------------------------------------------------------------------------
# Defaults & identity
# ---------------------------------------------------------------------------


def test_default_mapping_round_trips_unchanged() -> None:
    """Mapping that matches build_agenda_plan's defaults yields the same
    bucket contents."""
    f1 = _issue("PROJ-1", resolved=_utc(2026, 4, 10))
    o1 = _issue("PROJ-2", created=_utc(2026, 4, 5))
    plan = _default_plan([f1], [o1])

    mapping = {"PROJ-1": "mention", "PROJ-2": "open"}
    out = _apply_categorization(plan, mapping)

    assert [i.id_readable for i in out.demo] == []
    assert [i.id_readable for i in out.no_demo] == ["PROJ-1"]
    assert [i.id_readable for i in out.open] == ["PROJ-2"]
    assert [i.id_readable for i in out.excluded] == []
    assert out.filtered_count == plan.filtered_count
    assert out.collapsed_subtask_count == plan.collapsed_subtask_count


def test_empty_plan_with_empty_mapping_returns_empty_plan() -> None:
    plan = _default_plan([], [])
    out = _apply_categorization(plan, {})
    assert out.demo == out.no_demo == out.open == out.excluded == []


# ---------------------------------------------------------------------------
# Invariant violations
# ---------------------------------------------------------------------------


def test_mapping_missing_issue_raises_value_error() -> None:
    plan = _default_plan(
        [_issue("PROJ-1", resolved=_utc(2026, 4, 10))],
        [_issue("PROJ-2")],
    )
    with pytest.raises(ValueError, match="mapping mismatch"):
        _apply_categorization(plan, {"PROJ-1": "mention"})


def test_mapping_with_extra_issue_raises_value_error() -> None:
    plan = _default_plan([_issue("PROJ-1", resolved=_utc(2026, 4, 10))], [])
    with pytest.raises(ValueError, match="mapping mismatch"):
        _apply_categorization(
            plan, {"PROJ-1": "mention", "PROJ-999": "open"}
        )


def test_invalid_bucket_value_raises_value_error() -> None:
    plan = _default_plan([_issue("PROJ-1", resolved=_utc(2026, 4, 10))], [])
    with pytest.raises(ValueError, match="invalid bucket"):
        _apply_categorization(plan, {"PROJ-1": "nope"})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# In-bucket sort across cross-bucket moves
# ---------------------------------------------------------------------------


def test_cross_bucket_move_preserves_in_bucket_sort_finished_before_unresolved() -> None:
    """Spec 004: 'finished entries come first, then unresolved entries,
    each group in its natural sort' — even after a cross-bucket move."""
    # Two finished issues (will land in mention by default) and one open
    # (default open). Elevate the open one to present alongside one of the
    # finished issues.
    f_late = _issue("PROJ-A", resolved=_utc(2026, 4, 12))
    f_early = _issue("PROJ-B", resolved=_utc(2026, 4, 10))
    o = _issue("PROJ-C", created=_utc(2026, 4, 8))
    plan = _default_plan([f_early, f_late], [o])

    mapping = {
        "PROJ-A": "present",  # finished elevated
        "PROJ-B": "mention",  # default
        "PROJ-C": "present",  # open elevated
    }
    out = _apply_categorization(plan, mapping)

    # Present holds A (finished) then C (open). Finished sort by
    # (resolved_at, id_readable) puts PROJ-A alone in the finished half.
    assert [i.id_readable for i in out.demo] == ["PROJ-A", "PROJ-C"]
    assert [i.id_readable for i in out.no_demo] == ["PROJ-B"]
    assert out.open == []
    assert out.excluded == []


def test_finished_group_within_bucket_sorts_by_resolved_at() -> None:
    f_late = _issue("PROJ-A", resolved=_utc(2026, 4, 12))
    f_mid = _issue("PROJ-B", resolved=_utc(2026, 4, 11))
    f_early = _issue("PROJ-C", resolved=_utc(2026, 4, 10))
    plan = _default_plan([f_early, f_mid, f_late], [])

    # Elevate all to present.
    mapping = {"PROJ-A": "present", "PROJ-B": "present", "PROJ-C": "present"}
    out = _apply_categorization(plan, mapping)
    assert [i.id_readable for i in out.demo] == ["PROJ-C", "PROJ-B", "PROJ-A"]


def test_unresolved_group_within_bucket_sorts_by_created_at() -> None:
    o_late = _issue("PROJ-A", created=_utc(2026, 4, 12))
    o_mid = _issue("PROJ-B", created=_utc(2026, 4, 11))
    o_early = _issue("PROJ-C", created=_utc(2026, 4, 10))
    plan = _default_plan([], [o_early, o_mid, o_late])

    mapping = {"PROJ-A": "open", "PROJ-B": "open", "PROJ-C": "open"}
    out = _apply_categorization(plan, mapping)
    assert [i.id_readable for i in out.open] == ["PROJ-C", "PROJ-B", "PROJ-A"]


def test_excluded_bucket_collects_hidden_issues() -> None:
    f = _issue("PROJ-A", resolved=_utc(2026, 4, 10))
    o = _issue("PROJ-B")
    plan = _default_plan([f], [o])

    mapping = {"PROJ-A": "exclude", "PROJ-B": "exclude"}
    out = _apply_categorization(plan, mapping)
    assert out.demo == out.no_demo == out.open == []
    assert [i.id_readable for i in out.excluded] == ["PROJ-A", "PROJ-B"]


# ---------------------------------------------------------------------------
# Spec 005 — AgendaRow identity across re-categorization and log surface
# ---------------------------------------------------------------------------


def test_apply_categorization_reuses_same_agenda_row_across_buckets() -> None:
    """Spec 005: when a row moves bucket, the SAME AgendaRow instance is
    reused so any prior rename (display_title edit) survives."""
    issue = _issue("PROJ-A", resolved=_utc(2026, 4, 10))
    row = AgendaRow.from_issue(issue)
    row.display_title = "Renamed by user"  # simulate a prior rename
    plan = AgendaPlan(
        demo=[],
        no_demo=[row],
        open=[],
        excluded=[],
        unfiltered_count=1,
        filtered_count=1,
        collapsed_subtask_count=0,
    )

    out = _apply_categorization(plan, {"PROJ-A": "present"})

    assert out.no_demo == []
    assert len(out.demo) == 1
    assert out.demo[0] is row, "row must be the same instance, not a copy"
    assert out.demo[0].display_title == "Renamed by user"


def test_write_cross_reference_uses_display_title(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Spec 005: the cross-reference log line reads `display_title`, not
    the underlying issue title."""
    logger = logging.getLogger("test_xref")
    issue = _issue("PROJ-A", resolved=_utc(2026, 4, 10))
    row = AgendaRow.from_issue(issue)
    row.display_title = "Edited title"
    plan = AgendaPlan(no_demo=[row])

    with caplog.at_level(logging.INFO, logger="test_xref"):
        _write_cross_reference(logger, plan)

    log_text = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "Edited title" in log_text
    assert "PROJ-A" in log_text


def test_invariant_still_holds_with_collapsed_subtasks_in_counts() -> None:
    """`filtered_count - collapsed_subtask_count` must equal the sum of
    the four bucket lengths."""
    f = _issue("PROJ-A", resolved=_utc(2026, 4, 10))
    o = _issue("PROJ-B")
    plan = AgendaPlan(
        no_demo=[AgendaRow.from_issue(f)],
        open=[AgendaRow.from_issue(o)],
        unfiltered_count=5,
        filtered_count=3,  # one issue filtered out
        collapsed_subtask_count=1,  # one subtask collapsed
    )

    mapping = {"PROJ-A": "mention", "PROJ-B": "open"}
    out = _apply_categorization(plan, mapping)
    total = len(out.demo) + len(out.no_demo) + len(out.open) + len(out.excluded)
    assert total == out.filtered_count - out.collapsed_subtask_count == 2
