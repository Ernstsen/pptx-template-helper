"""Unit tests for CLI argument parsing (T031 / Iteration 3 / US3).

Iteration 3 introduces a single boolean flag, ``--pick-sprint``. Bare
invocation must keep the default flow (latest-by-end-date sprint per
FR-007); the flag flips the orchestration into picker mode.
"""

from __future__ import annotations

import pytest

from sprint_recap import app


def test_parse_args_default_keeps_default_flow() -> None:
    args = app.parse_args([])
    assert args.pick_sprint is False


def test_parse_args_pick_sprint_flag_sets_mode() -> None:
    args = app.parse_args(["--pick-sprint"])
    assert args.pick_sprint is True


def test_parse_args_unknown_flag_aborts() -> None:
    """Iteration 3 scope is one flag only; surface unknowns rather than
    silently ignoring them."""
    with pytest.raises(SystemExit):
        app.parse_args(["--no-such-flag"])
