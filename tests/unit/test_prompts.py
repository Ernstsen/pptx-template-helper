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

from sprint_recap import prompts


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
