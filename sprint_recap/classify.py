"""Build the AgendaPlan from raw sprint issues.

Pipeline (data-model.md §Lifecycle):
    pre-filter membership ids → apply IssueTypeFilter → filtered_count
    → drop in-sprint subtasks → collapsed_subtask_count
    → split by resolved_at → sort each per FR-020.

Subtask-collapse uses the *full* pre-filter membership: a parent that the
filter later excludes still hides its subtasks. The classification looks
only at `resolved_at` (FR-010 — never inspect state-name strings).
"""

from __future__ import annotations

import logging
from typing import Iterable, Sequence

from sprint_recap.models import AgendaPlan, IssueTypeFilter, SprintIssue

_log = logging.getLogger(__name__)


def _matches_filter(issue: SprintIssue, allowed_lower: set[str]) -> bool:
    return issue.issue_type.lower() in allowed_lower


def build_agenda_plan(
    issues: Sequence[SprintIssue],
    type_filter: IssueTypeFilter,
) -> AgendaPlan:
    unfiltered_count = len(issues)
    sprint_ids = {i.id_readable for i in issues}

    # Normalize empty list → "all" (data-model.md IssueTypeFilter rules).
    if isinstance(type_filter, list) and len(type_filter) == 0:
        _log.warning(
            "issue_type_filter is an empty list; treating as \"all\" (no filtering)"
        )
        type_filter = "all"

    if type_filter == "all":
        filtered: Iterable[SprintIssue] = list(issues)
    else:
        allowed_lower = {t.lower() for t in type_filter}
        filtered = [i for i in issues if _matches_filter(i, allowed_lower)]
    filtered_list = list(filtered)
    filtered_count = len(filtered_list)

    # Subtask collapse computed against the full pre-filter membership.
    collapsed: list[SprintIssue] = []
    collapsed_count = 0
    for issue in filtered_list:
        if issue.is_subtask_to_collapse(sprint_ids):
            collapsed_count += 1
            continue
        collapsed.append(issue)

    finished = sorted(
        (i for i in collapsed if i.is_finished),
        key=lambda i: (i.resolved_at, i.id_readable),
    )
    open_ = sorted(
        (i for i in collapsed if not i.is_finished),
        key=lambda i: (i.created_at, i.id_readable),
    )

    return AgendaPlan(
        finished=finished,
        open=open_,
        unfiltered_count=unfiltered_count,
        filtered_count=filtered_count,
        collapsed_subtask_count=collapsed_count,
    )
