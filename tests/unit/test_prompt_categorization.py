"""Spec 004 — `prompt_categorization` mapping contract.

The prompt returns a `dict[id_readable -> bucket]` covering every issue
across the four AgendaPlan bucket lists. Defaults follow `is_finished`
(finished → mention, unresolved → open). Cancel paths raise `ValueError`.

These tests use the same stub-injection style as `test_prompts.py`: the
curses `wrapper`/`curs_set` are monkeypatched and a fake `stdscr` drives
keystrokes; tkinter is replaced with a MagicMock in `sys.modules`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from sprint_recap import prompts
from sprint_recap.models import AgendaPlan, SprintIssue


@pytest.fixture(autouse=True)
def _reset_mode() -> None:
    prompts.reset_prompt_mode()
    yield
    prompts.reset_prompt_mode()


def _finished_issue(id_readable: str, title: str = "x") -> SprintIssue:
    return SprintIssue(
        id_readable=id_readable,
        title=title,
        issue_type="Story",
        parent_id_readable=None,
        resolved_at=datetime(2026, 4, 30, tzinfo=timezone.utc),
        created_at=datetime(2026, 4, 9, tzinfo=timezone.utc),
    )


def _open_issue(id_readable: str, title: str = "x") -> SprintIssue:
    return SprintIssue(
        id_readable=id_readable,
        title=title,
        issue_type="Story",
        parent_id_readable=None,
        resolved_at=None,
        created_at=datetime(2026, 4, 9, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Empty-input fast path
# ---------------------------------------------------------------------------


def test_prompt_categorization_empty_returns_empty_mapping() -> None:
    """All four buckets empty → skip the UI and return {}."""
    plan = AgendaPlan()
    assert prompts.prompt_categorization(plan) == {}


# ---------------------------------------------------------------------------
# Curses variant
# ---------------------------------------------------------------------------


def _install_fake_curses(monkeypatch: pytest.MonkeyPatch, keys: list[int]):
    """Wire a fake stdscr into the curses module and return it."""
    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (40, 120)
    key_iter = iter(keys)
    fake_stdscr.getch.side_effect = lambda: next(key_iter)

    import curses as _curses_mod

    monkeypatch.setattr(_curses_mod, "wrapper", lambda fn: fn(fake_stdscr))
    monkeypatch.setattr(_curses_mod, "curs_set", lambda _: None)
    return fake_stdscr


def test_console_defaults_finished_to_mention_unresolved_to_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    plan = AgendaPlan(
        no_demo=[_finished_issue("PROJ-1")],
        open=[_open_issue("PROJ-2")],
    )
    _install_fake_curses(monkeypatch, keys=[10])  # immediate Enter

    result = prompts.prompt_categorization(plan)
    assert result == {"PROJ-1": "mention", "PROJ-2": "open"}


def test_console_space_cycles_through_all_four_buckets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec 004: Space cycles Present → Mention → Open → Exclude → Present."""
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    plan = AgendaPlan(no_demo=[_finished_issue("PROJ-1")])
    # Start state: mention. Cycle order from mention: open, exclude, present.
    _install_fake_curses(
        monkeypatch,
        keys=[
            ord(" "),  # mention -> open
            ord(" "),  # open    -> exclude
            ord(" "),  # exclude -> present
            10,        # confirm
        ],
    )
    assert prompts.prompt_categorization(plan) == {"PROJ-1": "present"}


def test_console_cycle_wraps_present_after_exclude(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    plan = AgendaPlan(open=[_open_issue("PROJ-1")])
    # Start state: open. Cycle: exclude, present, mention, open.
    _install_fake_curses(
        monkeypatch,
        keys=[ord(" "), ord(" "), ord(" "), ord(" "), 10],
    )
    assert prompts.prompt_categorization(plan) == {"PROJ-1": "open"}


def test_console_navigation_moves_current_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """↓ then Space must cycle the second row, not the first."""
    import curses as _curses_mod

    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    plan = AgendaPlan(
        no_demo=[_finished_issue("PROJ-1"), _finished_issue("PROJ-2")]
    )
    _install_fake_curses(
        monkeypatch,
        keys=[_curses_mod.KEY_DOWN, ord(" "), 10],  # row 2, mention->open
    )
    result = prompts.prompt_categorization(plan)
    assert result == {"PROJ-1": "mention", "PROJ-2": "open"}


def test_console_q_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    plan = AgendaPlan(no_demo=[_finished_issue("PROJ-1")])
    _install_fake_curses(monkeypatch, keys=[ord("q")])

    with pytest.raises(ValueError, match="cancelled"):
        prompts.prompt_categorization(plan)


def test_console_mapping_covers_every_issue_across_all_input_buckets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Issues already pre-assigned to demo/no_demo/open/excluded all appear
    in the returned mapping with their starting bucket preserved."""
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    plan = AgendaPlan(
        demo=[_finished_issue("PROJ-A")],
        no_demo=[_finished_issue("PROJ-B")],
        open=[_open_issue("PROJ-C")],
        excluded=[_open_issue("PROJ-D")],
    )
    _install_fake_curses(monkeypatch, keys=[10])  # immediate Enter
    result = prompts.prompt_categorization(plan)
    assert result == {
        "PROJ-A": "present",
        "PROJ-B": "mention",
        "PROJ-C": "open",
        "PROJ-D": "exclude",
    }


# ---------------------------------------------------------------------------
# Tkinter variant
# ---------------------------------------------------------------------------


def _install_fake_tk(
    monkeypatch: pytest.MonkeyPatch,
    *,
    confirm: bool,
    radio_factory=None,
):
    """Install a MagicMock tkinter and wire up Button/wait_window."""
    fake_tk = MagicMock()

    string_vars: list[tuple[MagicMock, str]] = []

    def make_string_var(value: str = "") -> MagicMock:
        var = MagicMock()
        var.get.return_value = value
        var.set.side_effect = lambda v: setattr(var.get, "return_value", v)
        string_vars.append((var, value))
        return var

    fake_tk.StringVar.side_effect = make_string_var

    captured: dict[str, Any] = {"confirm": None, "cancel": None}

    def capture_button(parent, text, command, **kw):  # noqa: ARG001
        if text == "OK":
            captured["confirm"] = command
        elif text == "Cancel":
            captured["cancel"] = command
        return MagicMock()

    fake_tk.Button.side_effect = capture_button

    if radio_factory is not None:
        fake_tk.Radiobutton.side_effect = radio_factory(string_vars)

    def fake_wait_window(_top: Any) -> None:
        if confirm:
            captured["confirm"]()
        else:
            captured["cancel"]()

    fake_root = MagicMock()
    fake_root.wait_window.side_effect = fake_wait_window
    fake_tk.Tk.return_value = fake_root
    fake_tk.Toplevel.return_value = MagicMock()
    fake_tk.VERTICAL = "vertical"
    fake_tk.LEFT = "left"
    fake_tk.RIGHT = "right"
    fake_tk.BOTH = "both"
    fake_tk.X = "x"
    fake_tk.Y = "y"
    fake_tk.Frame.return_value = MagicMock()
    fake_tk.Label.return_value = MagicMock()
    fake_tk.Canvas.return_value = MagicMock()
    fake_tk.Scrollbar.return_value = MagicMock()
    fake_tk.Radiobutton.return_value = MagicMock()

    import sys as _sys

    monkeypatch.setitem(_sys.modules, "tkinter", fake_tk)
    return fake_tk, string_vars


def test_tkinter_defaults_then_confirm_returns_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)
    plan = AgendaPlan(
        no_demo=[_finished_issue("PROJ-1")],
        open=[_open_issue("PROJ-2")],
    )
    _install_fake_tk(monkeypatch, confirm=True)

    result = prompts.prompt_categorization(plan)
    assert result == {"PROJ-1": "mention", "PROJ-2": "open"}


def test_tkinter_user_changes_a_row_before_confirming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulate the user picking 'present' for PROJ-1 via the radio var."""
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)
    plan = AgendaPlan(
        no_demo=[_finished_issue("PROJ-1")],
        open=[_open_issue("PROJ-2")],
    )
    fake_tk, _ = _install_fake_tk(monkeypatch, confirm=True)

    # The first StringVar created is PROJ-1's (rows are built in iteration
    # order over demo + no_demo + open + excluded). Patch StringVar so we
    # can drive get() after the screen builds and before confirm runs.
    created: list[MagicMock] = []

    def make_var(value: str = "") -> MagicMock:
        var = MagicMock()
        var.get.return_value = value
        created.append(var)
        return var

    fake_tk.StringVar.side_effect = make_var

    # Override wait_window: flip PROJ-1's var to "present" then confirm.
    captured: dict[str, Any] = {}

    def capture_button(parent, text, command, **kw):  # noqa: ARG001
        if text == "OK":
            captured["confirm"] = command
        elif text == "Cancel":
            captured["cancel"] = command
        return MagicMock()

    fake_tk.Button.side_effect = capture_button

    def fake_wait_window(_top: Any) -> None:
        # created[0] is the header counts StringVar; created[1] is PROJ-1
        # (rows are emitted in order across demo + no_demo + open + excluded).
        created[1].get.return_value = "present"
        captured["confirm"]()

    fake_tk.Tk.return_value.wait_window.side_effect = fake_wait_window

    result = prompts.prompt_categorization(plan)
    assert result == {"PROJ-1": "present", "PROJ-2": "open"}


def test_tkinter_cancel_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)
    plan = AgendaPlan(no_demo=[_finished_issue("PROJ-1")])
    _install_fake_tk(monkeypatch, confirm=False)

    with pytest.raises(ValueError, match="cancelled"):
        prompts.prompt_categorization(plan)
