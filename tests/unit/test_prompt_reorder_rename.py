"""Spec 005 — `prompt_reorder_rename` console + tkinter behavior.

Uses the same stub-injection style as `test_prompt_categorization.py`:
the curses `wrapper` / `curs_set` / `newwin` are monkeypatched, a fake
`stdscr` drives keystrokes, and the Textbox edit path is replaced with
a stub that produces a deterministic answer. Tkinter is replaced by a
MagicMock in `sys.modules`.

The plan is mutated in place; tests inspect plan attributes after the
function returns.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from sprint_recap import prompts
from sprint_recap.models import AgendaPlan, AgendaRow, SprintIssue


@pytest.fixture(autouse=True)
def _reset_mode() -> None:
    prompts.reset_prompt_mode()
    yield
    prompts.reset_prompt_mode()


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def _row(
    id_readable: str,
    title: str = "x",
    *,
    resolved: datetime | None = None,
) -> AgendaRow:
    return AgendaRow.from_issue(
        SprintIssue(
            id_readable=id_readable,
            title=title,
            issue_type="Story",
            parent_id_readable=None,
            resolved_at=resolved or _utc(2026, 4, 30),
            created_at=_utc(2026, 4, 9),
        )
    )


# ---------------------------------------------------------------------------
# Empty fast-path
# ---------------------------------------------------------------------------


def test_empty_plan_returns_immediately_without_touching_ui() -> None:
    """All three editable buckets empty → skip the UI; excluded ignored."""
    plan = AgendaPlan(excluded=[_row("PROJ-X")])
    # If the UI were entered we'd blow up importing curses/tkinter.
    prompts.prompt_reorder_rename(plan)  # no raise


# ---------------------------------------------------------------------------
# Curses variant — fake stdscr drives keystrokes
# ---------------------------------------------------------------------------


def _install_fake_curses(monkeypatch: pytest.MonkeyPatch, keys: list[int]):
    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (40, 120)
    key_iter = iter(keys)
    fake_stdscr.getch.side_effect = lambda: next(key_iter)

    import curses as _curses_mod

    monkeypatch.setattr(_curses_mod, "wrapper", lambda fn: fn(fake_stdscr))
    monkeypatch.setattr(_curses_mod, "curs_set", lambda _: None)
    return fake_stdscr


def test_console_immediate_enter_returns_without_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    plan = AgendaPlan(no_demo=[_row("PROJ-1", "Alpha"), _row("PROJ-2", "Beta")])
    _install_fake_curses(monkeypatch, keys=[10])  # immediate Enter

    prompts.prompt_reorder_rename(plan)

    assert [r.id_readable for r in plan.no_demo] == ["PROJ-1", "PROJ-2"]
    assert [r.display_title for r in plan.no_demo] == ["Alpha", "Beta"]


def test_console_q_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    plan = AgendaPlan(no_demo=[_row("PROJ-1")])
    _install_fake_curses(monkeypatch, keys=[ord("q")])

    with pytest.raises(ValueError, match="cancelled"):
        prompts.prompt_reorder_rename(plan)


def test_console_shift_j_moves_row_down_within_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shift+J (move down) is the Alt+↓ fallback. Swaps row 0 with row 1
    inside the same bucket."""
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    plan = AgendaPlan(
        no_demo=[
            _row("PROJ-1", "Alpha"),
            _row("PROJ-2", "Beta"),
            _row("PROJ-3", "Gamma"),
        ]
    )
    _install_fake_curses(monkeypatch, keys=[ord("J"), 10])

    prompts.prompt_reorder_rename(plan)
    assert [r.id_readable for r in plan.no_demo] == [
        "PROJ-2",
        "PROJ-1",
        "PROJ-3",
    ]


def test_console_shift_j_at_section_end_is_silent_no_op(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pressing move-down on the last row in a section is a no-op (the
    spec forbids cross-bucket moves on this screen)."""
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    plan = AgendaPlan(
        no_demo=[_row("PROJ-1", "A")],
        open=[_row("PROJ-2", "B")],
    )
    # Cursor starts on first row (PROJ-1, last in no_demo). Move down
    # would cross into the open bucket → must be a no-op.
    _install_fake_curses(monkeypatch, keys=[ord("J"), 10])

    prompts.prompt_reorder_rename(plan)
    assert [r.id_readable for r in plan.no_demo] == ["PROJ-1"]
    assert [r.id_readable for r in plan.open] == ["PROJ-2"]


def test_console_navigation_then_shift_k_moves_second_row_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """↓ then Shift+K swaps row 2 with row 1 (move up within section)."""
    import curses as _curses_mod

    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    plan = AgendaPlan(
        no_demo=[
            _row("PROJ-1", "Alpha"),
            _row("PROJ-2", "Beta"),
        ]
    )
    _install_fake_curses(
        monkeypatch,
        keys=[_curses_mod.KEY_DOWN, ord("K"), 10],
    )

    prompts.prompt_reorder_rename(plan)
    assert [r.id_readable for r in plan.no_demo] == ["PROJ-2", "PROJ-1"]


def test_console_rename_updates_display_title_keeps_issue_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`e` opens the inline editor; the returned text becomes display_title.
    The underlying issue's title is never touched."""
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    plan = AgendaPlan(no_demo=[_row("PROJ-1", "Original")])
    _install_fake_curses(monkeypatch, keys=[ord("e"), 10])

    # Stub the inline editor to return a new title.
    monkeypatch.setattr(
        prompts, "_curses_inline_edit", lambda *a, **kw: "Edited title"
    )

    prompts.prompt_reorder_rename(plan)
    assert plan.no_demo[0].display_title == "Edited title"
    assert plan.no_demo[0].issue.title == "Original"


def test_console_rename_with_whitespace_keeps_original(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    plan = AgendaPlan(no_demo=[_row("PROJ-1", "Original")])
    _install_fake_curses(monkeypatch, keys=[ord("e"), 10])

    # User typed only whitespace.
    monkeypatch.setattr(prompts, "_curses_inline_edit", lambda *a, **kw: "   ")

    prompts.prompt_reorder_rename(plan)
    assert plan.no_demo[0].display_title == "Original"


def test_console_rename_escape_keeps_original(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The inline editor returns None on Esc → display_title untouched."""
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    plan = AgendaPlan(no_demo=[_row("PROJ-1", "Original")])
    _install_fake_curses(monkeypatch, keys=[ord("e"), 10])

    monkeypatch.setattr(prompts, "_curses_inline_edit", lambda *a, **kw: None)

    prompts.prompt_reorder_rename(plan)
    assert plan.no_demo[0].display_title == "Original"


def test_console_does_not_show_or_touch_excluded_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Excluded rows must never appear in the flat row layout, so cursor
    navigation can't reach them."""
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    excluded_row = _row("PROJ-X", "do-not-touch")
    plan = AgendaPlan(no_demo=[_row("PROJ-1", "A")], excluded=[excluded_row])

    # Press ↓ a bunch of times to try to navigate into excluded, then
    # Shift+J to attempt a move, then confirm.
    keys = [ord("j"), ord("j"), ord("j"), ord("J"), 10]
    _install_fake_curses(monkeypatch, keys=keys)

    prompts.prompt_reorder_rename(plan)
    # Excluded list unchanged; row instance unchanged.
    assert plan.excluded == [excluded_row]
    assert plan.excluded[0].display_title == "do-not-touch"


# ---------------------------------------------------------------------------
# Tkinter variant — MagicMock screen
# ---------------------------------------------------------------------------


def _install_fake_tk(
    monkeypatch: pytest.MonkeyPatch,
    *,
    confirm: bool,
    rename_value: str | None = None,
):
    """Install a MagicMock tkinter + simpledialog + messagebox. Returns
    `(fake_tk, captured)`. `captured["confirm"]` and `captured["cancel"]`
    are filled in when the prompt registers its OK / Cancel buttons.
    """
    fake_tk = MagicMock()
    fake_simpledialog = MagicMock()
    fake_messagebox = MagicMock()

    fake_simpledialog.askstring.return_value = rename_value
    # `from tkinter import simpledialog, messagebox` binds via getattr on
    # the parent module — wire both explicitly.
    fake_tk.simpledialog = fake_simpledialog
    fake_tk.messagebox = fake_messagebox

    listboxes: list[MagicMock] = []

    def make_listbox(*a, **kw):  # noqa: ARG001
        lb = MagicMock()
        lb.curselection.return_value = ()
        listboxes.append(lb)
        return lb

    fake_tk.Listbox.side_effect = make_listbox

    captured: dict[str, Any] = {
        "confirm": None,
        "cancel": None,
        "buttons": [],
        "listboxes": listboxes,
    }

    def capture_button(parent, text, command, **kw):  # noqa: ARG001
        captured["buttons"].append((text, command))
        if text == "OK":
            captured["confirm"] = command
        elif text == "Cancel":
            captured["cancel"] = command
        return MagicMock()

    fake_tk.Button.side_effect = capture_button

    def fake_wait_window(_top: Any) -> None:
        if confirm:
            captured["confirm"]()
        else:
            captured["cancel"]()

    fake_root = MagicMock()
    fake_root.wait_window.side_effect = fake_wait_window
    fake_tk.Tk.return_value = fake_root
    fake_tk.Toplevel.return_value = MagicMock()
    fake_tk.Frame.return_value = MagicMock()
    fake_tk.Label.return_value = MagicMock()
    fake_tk.END = "end"
    fake_tk.LEFT = "left"
    fake_tk.BOTH = "both"
    fake_tk.X = "x"

    import sys as _sys

    monkeypatch.setitem(_sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(_sys.modules, "tkinter.messagebox", fake_messagebox)
    monkeypatch.setitem(_sys.modules, "tkinter.simpledialog", fake_simpledialog)

    return fake_tk, captured


def test_tkinter_ok_returns_with_plan_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)
    plan = AgendaPlan(no_demo=[_row("PROJ-1", "A"), _row("PROJ-2", "B")])
    _install_fake_tk(monkeypatch, confirm=True)

    prompts.prompt_reorder_rename(plan)
    assert [r.id_readable for r in plan.no_demo] == ["PROJ-1", "PROJ-2"]


def test_tkinter_cancel_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)
    plan = AgendaPlan(no_demo=[_row("PROJ-1")])
    _install_fake_tk(monkeypatch, confirm=False)

    with pytest.raises(ValueError, match="cancelled"):
        prompts.prompt_reorder_rename(plan)


def test_tkinter_move_button_swaps_rows_within_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ↓ button under the Mention listbox swaps its selected row with
    the next one. We drive the button by selecting row 0 in that listbox
    and invoking the captured command."""
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)
    plan = AgendaPlan(
        no_demo=[
            _row("PROJ-1", "Alpha"),
            _row("PROJ-2", "Beta"),
        ]
    )
    fake_tk, captured = _install_fake_tk(monkeypatch, confirm=True)

    # Override wait_window to: select row 0 in the no_demo listbox, fire
    # its ↓ button, then confirm.
    def fake_wait_window(_top: Any) -> None:
        # Listboxes are created in display order: demo (empty UI still
        # builds it), no_demo, open. Find them by build order.
        lbs = captured["listboxes"]
        # Buttons are appended in build order, three per section
        # (↑, ↓, Rename…), plus OK / Cancel at the end.
        buttons = captured["buttons"]
        # Demo section adds 3 buttons, no_demo section adds 3, then open
        # adds 3, then OK + Cancel.
        # ↓ for no_demo is buttons[3 + 1] = buttons[4].
        # Select row 0 in the no_demo listbox (lbs[1]).
        lbs[1].curselection.return_value = (0,)
        # Invoke the no_demo ↓ button (the 5th, index 4).
        _, cmd = buttons[4]
        cmd()
        captured["confirm"]()

    fake_tk.Tk.return_value.wait_window.side_effect = fake_wait_window

    prompts.prompt_reorder_rename(plan)
    assert [r.id_readable for r in plan.no_demo] == ["PROJ-2", "PROJ-1"]


def test_tkinter_rename_button_updates_display_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)
    plan = AgendaPlan(no_demo=[_row("PROJ-1", "Original")])
    fake_tk, captured = _install_fake_tk(
        monkeypatch, confirm=True, rename_value="Edited"
    )

    def fake_wait_window(_top: Any) -> None:
        lbs = captured["listboxes"]
        buttons = captured["buttons"]
        # Select row 0 in no_demo listbox.
        lbs[1].curselection.return_value = (0,)
        # Rename… for no_demo is the third button in that section, so
        # buttons[3 + 2] = buttons[5].
        _, cmd = buttons[5]
        cmd()
        captured["confirm"]()

    fake_tk.Tk.return_value.wait_window.side_effect = fake_wait_window

    prompts.prompt_reorder_rename(plan)
    assert plan.no_demo[0].display_title == "Edited"
    assert plan.no_demo[0].issue.title == "Original"


def test_tkinter_rename_whitespace_keeps_original_and_shows_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)
    plan = AgendaPlan(no_demo=[_row("PROJ-1", "Original")])
    fake_tk, captured = _install_fake_tk(
        monkeypatch, confirm=True, rename_value="   "
    )

    def fake_wait_window(_top: Any) -> None:
        lbs = captured["listboxes"]
        buttons = captured["buttons"]
        lbs[1].curselection.return_value = (0,)
        _, cmd = buttons[5]
        cmd()
        captured["confirm"]()

    fake_tk.Tk.return_value.wait_window.side_effect = fake_wait_window

    prompts.prompt_reorder_rename(plan)
    assert plan.no_demo[0].display_title == "Original"
    # messagebox.showerror should have been called at least once.
    assert fake_tk.messagebox.showerror.call_count >= 1
