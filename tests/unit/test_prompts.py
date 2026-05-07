"""Unit tests for the prompt facade (T022).

The prompt mode is auto-detected once at startup via sys.stdin.isatty()
(FR-012 / research §R3) and held constant for the run. These tests
verify:

- console mode numbered-list selection returns the chosen item
- tkinter mode (mocked) returns the chosen item
- chosen mode is computed once and module-level
- cancel returns the cancel sentinel (None) so the caller aborts without
  writing files (FR-016 / FR-014)
- prompt_text returns text in console (input()) and tkinter
  (simpledialog.askstring) without ever asking for the token
"""

from __future__ import annotations

import io
from typing import Any
from unittest.mock import MagicMock

import pytest

from datetime import date

from sprint_recap import prompts
from sprint_recap.models import Sprint


@pytest.fixture(autouse=True)
def _reset_mode() -> None:
    """Each test re-detects the prompt mode."""
    prompts.reset_prompt_mode()
    yield
    prompts.reset_prompt_mode()


# ---------------------------------------------------------------------------
# detect_prompt_mode
# ---------------------------------------------------------------------------


def test_detect_prompt_mode_console_when_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    assert prompts.detect_prompt_mode() == "console"


def test_detect_prompt_mode_tkinter_when_not_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)
    assert prompts.detect_prompt_mode() == "tkinter"


def test_detect_prompt_mode_is_cached_after_first_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-012: mode is computed once and held constant for the run."""
    isatty_calls: list[bool] = []

    def spy_isatty() -> bool:
        isatty_calls.append(True)
        return True

    monkeypatch.setattr(prompts.sys.stdin, "isatty", spy_isatty)
    first = prompts.detect_prompt_mode()
    # Now flip the underlying value; the cached mode must persist.
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)
    second = prompts.detect_prompt_mode()
    assert first == second == "console"
    assert len(isatty_calls) == 1


# ---------------------------------------------------------------------------
# prompt_choice — console mode
# ---------------------------------------------------------------------------


def test_console_choice_returns_selected_option(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "2")
    pick = prompts.prompt_choice("Pick one:", ["alpha", "beta", "gamma"])
    assert pick == "beta"


def test_console_choice_cancel_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "0")
    assert prompts.prompt_choice("Pick:", ["a", "b"]) is None


def test_console_choice_empty_input_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert prompts.prompt_choice("Pick:", ["a", "b"]) is None


def test_console_choice_reprompts_on_bad_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    answers = iter(["nope", "999", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert prompts.prompt_choice("Pick:", ["a", "b"]) == "a"


# ---------------------------------------------------------------------------
# prompt_choice — tkinter mode (mocked)
# ---------------------------------------------------------------------------


def test_tkinter_choice_returns_selected_option(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)

    fake_tk = MagicMock()
    fake_messagebox = MagicMock()

    # Listbox.curselection() returns the second item.
    fake_listbox = MagicMock()
    fake_listbox.curselection.return_value = (1,)
    fake_tk.Listbox.return_value = fake_listbox

    # Confirm wiring: when wait_window is called, simulate the user
    # clicking OK by invoking the most recently-registered confirm command.
    captured = {"confirm": None, "cancel": None}

    def capture_button(parent, text, command, **kw):  # noqa: ARG001
        if text == "OK":
            captured["confirm"] = command
        elif text == "Cancel":
            captured["cancel"] = command
        return MagicMock()

    fake_tk.Button.side_effect = capture_button

    def fake_wait_window(_top: Any) -> None:
        # Simulate user clicking OK.
        captured["confirm"]()

    fake_root = MagicMock()
    fake_root.wait_window.side_effect = fake_wait_window
    fake_tk.Tk.return_value = fake_root

    fake_top = MagicMock()
    fake_tk.Toplevel.return_value = fake_top
    fake_tk.END = "end"
    fake_tk.LEFT = "left"
    fake_tk.BOTH = "both"
    fake_tk.Frame.return_value = MagicMock()
    fake_tk.Label.return_value = MagicMock()

    import sys as _sys

    monkeypatch.setitem(_sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(_sys.modules, "tkinter.messagebox", fake_messagebox)

    pick = prompts.prompt_choice("Pick:", ["alpha", "beta", "gamma"])
    assert pick == "beta"


def test_tkinter_choice_cancel_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)

    fake_tk = MagicMock()
    fake_messagebox = MagicMock()

    fake_listbox = MagicMock()
    fake_listbox.curselection.return_value = ()
    fake_tk.Listbox.return_value = fake_listbox

    captured = {"confirm": None, "cancel": None}

    def capture_button(parent, text, command, **kw):  # noqa: ARG001
        if text == "OK":
            captured["confirm"] = command
        elif text == "Cancel":
            captured["cancel"] = command
        return MagicMock()

    fake_tk.Button.side_effect = capture_button

    def fake_wait_window(_top: Any) -> None:
        captured["cancel"]()

    fake_root = MagicMock()
    fake_root.wait_window.side_effect = fake_wait_window
    fake_tk.Tk.return_value = fake_root
    fake_tk.Toplevel.return_value = MagicMock()
    fake_tk.END = "end"
    fake_tk.LEFT = "left"
    fake_tk.BOTH = "both"
    fake_tk.Frame.return_value = MagicMock()
    fake_tk.Label.return_value = MagicMock()

    import sys as _sys

    monkeypatch.setitem(_sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(_sys.modules, "tkinter.messagebox", fake_messagebox)

    assert prompts.prompt_choice("Pick:", ["alpha", "beta"]) is None


# ---------------------------------------------------------------------------
# prompt_text
# ---------------------------------------------------------------------------


def test_console_prompt_text_returns_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "https://yt.example.com")
    assert prompts.prompt_text("YouTrack URL:") == "https://yt.example.com"


def test_console_prompt_text_empty_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert prompts.prompt_text("YouTrack URL:") is None


def test_console_prompt_text_strips_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "   PROJ   ")
    assert prompts.prompt_text("Project:") == "PROJ"


def test_tkinter_prompt_text_uses_simpledialog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)

    fake_tk = MagicMock()
    fake_simpledialog = MagicMock()
    fake_simpledialog.askstring.return_value = "PROJ"
    # `from tkinter import simpledialog` binds via getattr on the parent
    # module if it has the attribute (MagicMock always does), so wire it
    # explicitly rather than relying on sys.modules submodule resolution.
    fake_tk.simpledialog = fake_simpledialog

    import sys as _sys

    monkeypatch.setitem(_sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(_sys.modules, "tkinter.simpledialog", fake_simpledialog)

    assert prompts.prompt_text("Project:") == "PROJ"
    assert fake_simpledialog.askstring.call_count == 1


def test_tkinter_prompt_text_cancel_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)

    fake_tk = MagicMock()
    fake_simpledialog = MagicMock()
    fake_simpledialog.askstring.return_value = None  # user clicked Cancel
    fake_tk.simpledialog = fake_simpledialog

    import sys as _sys

    monkeypatch.setitem(_sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(_sys.modules, "tkinter.simpledialog", fake_simpledialog)

    assert prompts.prompt_text("Project:") is None


# ---------------------------------------------------------------------------
# prompt_sprint (T030 / Iteration 3 / US3)
# ---------------------------------------------------------------------------


def _sprint(id_: str, name: str, start: date, end: date) -> Sprint:
    return Sprint(id=id_, name=name, start=start, end=end, archived=False)


def test_prompt_sprint_orders_by_end_date_descending(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Latest-by-end-date sprint appears first so the FR-007 default is at
    index 0 visually. Each line shows ``name (start_iso → end_iso)``."""
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    sprints = [
        _sprint("121-1", "Sprint 40", date(2026, 2, 1), date(2026, 3, 1)),
        _sprint("121-2", "Sprint 41", date(2026, 3, 2), date(2026, 4, 7)),
        _sprint("121-3", "Sprint 42", date(2026, 4, 8), date(2026, 5, 5)),
    ]
    monkeypatch.setattr("builtins.input", lambda _: "1")

    chosen = prompts.prompt_sprint(sprints)

    assert chosen is sprints[2], "latest-by-end-date sprint must be index 0"
    out = capsys.readouterr().out
    s42_pos = out.index("Sprint 42 (2026-04-08 → 2026-05-05)")
    s41_pos = out.index("Sprint 41 (2026-03-02 → 2026-04-07)")
    s40_pos = out.index("Sprint 40 (2026-02-01 → 2026-03-01)")
    assert s42_pos < s41_pos < s40_pos


def test_prompt_sprint_returns_selected_sprint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    sprints = [
        _sprint("121-1", "Sprint 40", date(2026, 2, 1), date(2026, 3, 1)),
        _sprint("121-2", "Sprint 41", date(2026, 3, 2), date(2026, 4, 7)),
        _sprint("121-3", "Sprint 42", date(2026, 4, 8), date(2026, 5, 5)),
    ]
    # After sorting by end-date desc, index 2 in the prompt list is Sprint 40.
    monkeypatch.setattr("builtins.input", lambda _: "3")
    chosen = prompts.prompt_sprint(sprints)
    assert chosen is sprints[0]


def test_prompt_sprint_single_sprint_still_prompts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With one closed sprint the picker still appears (per Independent
    Test in tasks.md / Iteration 3)."""
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    only = _sprint("121-9", "Sprint 1", date(2026, 1, 1), date(2026, 1, 31))
    monkeypatch.setattr("builtins.input", lambda _: "1")
    assert prompts.prompt_sprint([only]) is only


def test_prompt_sprint_cancel_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    sprints = [
        _sprint("121-1", "Sprint 40", date(2026, 2, 1), date(2026, 3, 1)),
    ]
    monkeypatch.setattr("builtins.input", lambda _: "0")
    assert prompts.prompt_sprint(sprints) is None


def test_prompt_sprint_empty_list_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: True)
    assert prompts.prompt_sprint([]) is None


def test_prompt_sprint_tkinter_uses_listbox(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prompts.sys.stdin, "isatty", lambda: False)
    sprints = [
        _sprint("121-1", "Sprint 40", date(2026, 2, 1), date(2026, 3, 1)),
        _sprint("121-2", "Sprint 41", date(2026, 3, 2), date(2026, 4, 7)),
    ]

    fake_tk = MagicMock()
    fake_messagebox = MagicMock()
    fake_listbox = MagicMock()
    fake_listbox.curselection.return_value = (0,)  # latest-by-end-date
    fake_tk.Listbox.return_value = fake_listbox

    captured: dict[str, Any] = {"confirm": None, "cancel": None}

    def capture_button(parent, text, command, **kw):  # noqa: ARG001
        if text == "OK":
            captured["confirm"] = command
        elif text == "Cancel":
            captured["cancel"] = command
        return MagicMock()

    fake_tk.Button.side_effect = capture_button

    def fake_wait_window(_top: Any) -> None:
        captured["confirm"]()

    fake_root = MagicMock()
    fake_root.wait_window.side_effect = fake_wait_window
    fake_tk.Tk.return_value = fake_root
    fake_tk.Toplevel.return_value = MagicMock()
    fake_tk.END = "end"
    fake_tk.LEFT = "left"
    fake_tk.BOTH = "both"
    fake_tk.Frame.return_value = MagicMock()
    fake_tk.Label.return_value = MagicMock()

    import sys as _sys

    monkeypatch.setitem(_sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(_sys.modules, "tkinter.messagebox", fake_messagebox)

    chosen = prompts.prompt_sprint(sprints)
    assert chosen is sprints[1]  # Sprint 41 (latest by end date)

    inserted_labels = [c.args[1] for c in fake_listbox.insert.call_args_list]
    assert inserted_labels == [
        "Sprint 41 (2026-03-02 → 2026-04-07)",
        "Sprint 40 (2026-02-01 → 2026-03-01)",
    ]
