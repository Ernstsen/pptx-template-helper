"""In-memory entities the program manipulates. Mirrors data-model.md.

External representations (settings JSON, log file, pptx tokens, YouTrack
JSON) live in their respective contracts under
specs/001-sprint-recap-deck/contracts/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Literal, Optional, Union


@dataclass(frozen=True)
class Sprint:
    id: str
    name: str
    start: date
    end: date
    archived: bool


@dataclass(frozen=True)
class SprintIssue:
    id_readable: str
    title: str
    issue_type: str
    parent_id_readable: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime

    @property
    def is_finished(self) -> bool:
        # FR-010: classification MUST NOT inspect any state-name string.
        return self.resolved_at is not None

    def is_subtask_to_collapse(self, sprint_ids: Iterable[str]) -> bool:
        if self.parent_id_readable is None:
            return False
        if not isinstance(sprint_ids, (set, frozenset)):
            sprint_ids = set(sprint_ids)
        return self.parent_id_readable in sprint_ids


# IssueTypeFilter is a *value*, not a wrapping dataclass: either the literal
# string "all" or a list[str]. The data-model file documents that empty lists
# get coerced to "all" with a logged WARN; that coercion happens in config.py
# at load time so consumers see only normalized values.
IssueTypeFilter = Union[Literal["all"], list[str]]


# Four-bucket categorization (spec 004). Each issue surviving the type filter
# and subtask collapse is assigned exactly one bucket via the categorization
# prompt. The internal AgendaPlan field names (demo/no_demo/open) stay as they
# are to avoid churning the renderer and existing tests; only the user-facing
# labels in the prompt and log use the bucket names.
AgendaBucket = Literal["present", "mention", "open", "exclude"]


@dataclass
class SavedSettings:
    youtrack_url: str
    project_id: str
    project_short_name: str
    board_id: str
    board_name: str
    issue_type_filter: IssueTypeFilter = "all"
    last_sprint_id: Optional[str] = None
    schema_version: int = 1


@dataclass
class AgendaRow:
    """Spec 005 per-bucket display wrapper.

    Pairs a `SprintIssue` with a mutable `display_title` so the user can
    rename the bullet shown on the deck (and recorded in the per-run log)
    without mutating the read-only issue payload from YouTrack. The
    rename is local to one run; nothing is persisted.

    `id_readable` and `is_finished` are proxied through to the wrapped
    issue so callers that previously took raw `SprintIssue` lists keep
    working with minimal changes.
    """

    issue: SprintIssue
    display_title: str  # initialized to issue.title

    @classmethod
    def from_issue(cls, issue: SprintIssue) -> "AgendaRow":
        return cls(issue=issue, display_title=issue.title)

    @property
    def id_readable(self) -> str:
        return self.issue.id_readable

    @property
    def is_finished(self) -> bool:
        return self.issue.is_finished


@dataclass
class AgendaPlan:
    demo: list[AgendaRow] = field(default_factory=list)
    no_demo: list[AgendaRow] = field(default_factory=list)
    open: list[AgendaRow] = field(default_factory=list)
    excluded: list[AgendaRow] = field(default_factory=list)
    unfiltered_count: int = 0
    filtered_count: int = 0
    collapsed_subtask_count: int = 0


@dataclass
class RunInputs:
    working_folder: Path
    template_path: Path
    settings: SavedSettings
    token: str
    sprint: Sprint
    issues: list[SprintIssue]
    prompt_mode: Literal["console", "tkinter"]
    output_path: Path
    log_path: Path
