"""Console + tkinter prompt facade.

Mode is detected once at startup via `sys.stdin.isatty()` per FR-012 and
research §R3, and is held constant for the run. Iteration 1 covers
template discovery and the overwrite confirmation; first-time-setup
prompts and the sprint picker arrive in later iterations and reuse the
same facade.
"""

from __future__ import annotations

import curses
import logging
import sys
from pathlib import Path
from typing import Literal, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from sprint_recap.models import Sprint, SprintIssue

_log = logging.getLogger(__name__)

PromptMode = Literal["console", "tkinter"]
OverwriteChoice = Literal["overwrite", "save_as", "cancel"]

_PROMPT_MODE: Optional[PromptMode] = None


def detect_prompt_mode() -> PromptMode:
    """Compute the prompt mode once and cache it (FR-012)."""
    global _PROMPT_MODE
    if _PROMPT_MODE is None:
        try:
            is_tty = sys.stdin is not None and sys.stdin.isatty()
        except AttributeError:
            is_tty = False
        _PROMPT_MODE = "console" if is_tty else "tkinter"
    return _PROMPT_MODE


def reset_prompt_mode() -> None:
    """Test seam — clears the cached mode so tests can re-detect."""
    global _PROMPT_MODE
    _PROMPT_MODE = None


def _console_choice(label: str, options: Sequence[str]) -> Optional[str]:
    print(label)
    for i, option in enumerate(options, start=1):
        print(f"  {i}. {option}")
    print("  0. cancel")
    while True:
        raw = input("Choose: ").strip()
        if raw in ("", "0", "q", "Q"):
            return None
        try:
            idx = int(raw)
        except ValueError:
            print(f"  '{raw}' is not a number, try again.")
            continue
        if 1 <= idx <= len(options):
            return options[idx - 1]
        print(f"  {idx} is out of range, try again.")


def _tkinter_choice(label: str, options: Sequence[str]) -> Optional[str]:
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    top = tk.Toplevel(root)
    top.title("sprint-recap")
    tk.Label(top, text=label).pack(padx=8, pady=8)
    listbox = tk.Listbox(top, height=min(10, max(3, len(options))))
    for opt in options:
        listbox.insert(tk.END, opt)
    listbox.pack(padx=8, pady=4, fill=tk.BOTH, expand=True)

    chosen: dict[str, Optional[str]] = {"value": None}

    def confirm() -> None:
        sel = listbox.curselection()
        if not sel:
            messagebox.showerror("sprint-recap", "Pick one item or cancel.", parent=top)
            return
        chosen["value"] = options[sel[0]]
        top.destroy()

    def cancel() -> None:
        top.destroy()

    button_frame = tk.Frame(top)
    button_frame.pack(pady=4)
    tk.Button(button_frame, text="OK", command=confirm).pack(side=tk.LEFT, padx=4)
    tk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.LEFT, padx=4)

    top.protocol("WM_DELETE_WINDOW", cancel)
    top.grab_set()
    root.wait_window(top)
    root.destroy()
    return chosen["value"]


def prompt_choice(label: str, options: Sequence[str]) -> Optional[str]:
    """Generic choose-one-of-many prompt. Returns None on cancel."""
    if not options:
        return None
    mode = detect_prompt_mode()
    if mode == "console":
        return _console_choice(label, options)
    return _tkinter_choice(label, options)


def prompt_text(
    label: str,
    default: Optional[str] = None,
    secret: bool = False,
) -> Optional[str]:
    """Free-text prompt (e.g. YouTrack URL, project short name).

    Returns the trimmed string the user typed, or None if they cancelled
    or left the field empty. The token is NEVER prompted — `secret=True`
    is reserved for any future use and is honored only by switching to
    `getpass`/masked input; FR-016 requires the token to come from the
    environment.
    """
    mode = detect_prompt_mode()
    if mode == "console":
        suffix = f" [{default}]" if default else ""
        if secret:
            from getpass import getpass

            raw = getpass(f"{label}{suffix} ")
        else:
            raw = input(f"{label}{suffix} ")
        raw = raw.strip()
        if not raw:
            return default if default else None
        return raw

    import tkinter as tk
    from tkinter import simpledialog

    root = tk.Tk()
    root.withdraw()
    try:
        raw = simpledialog.askstring(
            "sprint-recap",
            label,
            initialvalue=default or "",
            show="*" if secret else None,
        )
    finally:
        root.destroy()
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return default if default else None
    return raw


def show_error(message: str) -> None:
    """Surface a fatal error in whichever prompt mode is active.

    Console: writes a single line to stderr.
    Tkinter: shows a `messagebox.showerror` dialog so a double-click user
    actually sees the failure (otherwise the program appears to do
    nothing). Used by the FR-016 missing-token path and other abort
    surfaces during first-time setup.
    """
    mode = detect_prompt_mode()
    if mode == "console":
        sys.stderr.write(message + "\n")
        return
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    try:
        messagebox.showerror("sprint-recap", message)
    finally:
        root.destroy()


def find_template(working_folder: Path) -> Path:
    """Locate the pptx template in the working folder per FR-002.

    Zero pptx → prompt for path or abort.
    One pptx   → use it.
    Many pptx  → numbered selection (console) or listbox (tkinter).
    """
    pptx_files = sorted(p for p in working_folder.iterdir() if p.suffix.lower() == ".pptx")

    if len(pptx_files) == 1:
        chosen = pptx_files[0]
        _log.info("template = %s", chosen)
        return chosen

    if len(pptx_files) == 0:
        # Fall back to a free-text path prompt; in console we use input(),
        # in tkinter we use simpledialog.
        mode = detect_prompt_mode()
        if mode == "console":
            print(
                f"No .pptx files found in {working_folder}. "
                "Type the absolute path of a template or press Enter to abort."
            )
            raw = input("Template path: ").strip()
            if not raw:
                raise FileNotFoundError(
                    f"No .pptx template in {working_folder} and none was supplied."
                )
            path = Path(raw)
        else:
            import tkinter as tk
            from tkinter import simpledialog

            root = tk.Tk()
            root.withdraw()
            raw = simpledialog.askstring(
                "sprint-recap",
                f"No .pptx in {working_folder}.\nEnter a template path:",
            )
            root.destroy()
            if not raw:
                raise FileNotFoundError(
                    f"No .pptx template in {working_folder} and none was supplied."
                )
            path = Path(raw)
        if not path.exists():
            raise FileNotFoundError(f"Template not found at {path}")
        _log.info("template = %s", path)
        return path

    # Multiple .pptx files in the folder.
    labels = [str(p.name) for p in pptx_files]
    chosen_label = prompt_choice(
        f"Multiple .pptx files in {working_folder}; pick the template:", labels
    )
    if chosen_label is None:
        raise FileNotFoundError("User cancelled template selection.")
    chosen = pptx_files[labels.index(chosen_label)]
    _log.info("template = %s", chosen)
    return chosen


def prompt_sprint(sprints: Sequence["Sprint"]) -> Optional["Sprint"]:
    """Pick a sprint from the configured board (T033 / US3 / FR-007).

    Sprints are presented sorted by end date *descending* so the
    latest-by-end-date sprint (the FR-007 default) is at index 0
    visually. Each entry is rendered as ``name (start_iso → end_iso)``.

    Returns the chosen ``Sprint`` or ``None`` if the user cancelled. The
    caller must abort without writing files on cancel (Iteration 3
    Independent Test).
    """
    if not sprints:
        return None
    ordered = sorted(sprints, key=lambda s: s.end, reverse=True)
    labels = [
        f"{s.name} ({s.start.isoformat()} → {s.end.isoformat()})" for s in ordered
    ]
    chosen_label = prompt_choice("Pick a sprint to recap:", labels)
    if chosen_label is None:
        return None
    return ordered[labels.index(chosen_label)]


def confirm_overwrite(path: Path) -> OverwriteChoice:
    """Three-way confirmation: overwrite / save_as / cancel (FR-004)."""
    options = ["overwrite", "save under a different name", "cancel"]
    label = f"Output file already exists: {path}\nWhat do you want to do?"
    pick = prompt_choice(label, options)
    if pick is None or pick == "cancel":
        return "cancel"
    if pick == "overwrite":
        return "overwrite"
    return "save_as"


def _console_demo_selection(finished: Sequence["SprintIssue"]) -> set[str]:
    selected: set[int] = set()
    current = 0
    items = list(finished)

    def draw(stdscr: curses.window) -> set[str]:
        nonlocal current
        curses.curs_set(0)
        while True:
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            stdscr.addnstr(0, 0, "Select issues to demo (Space=toggle, Enter=confirm, q=cancel)", width - 1)
            for idx, issue in enumerate(items):
                if idx + 2 >= height:
                    break
                marker = "[x]" if idx in selected else "[ ]"
                line = f"{marker} {issue.id_readable}  {issue.title}"
                attr = curses.A_REVERSE if idx == current else 0
                stdscr.addnstr(idx + 2, 0, line, width - 1, attr)
            stdscr.refresh()
            key = stdscr.getch()
            if key == ord("q"):
                raise ValueError("User cancelled demo selection.")
            if key in (curses.KEY_UP, ord("k")):
                current = max(0, current - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                current = min(len(items) - 1, current + 1)
            elif key == ord(" "):
                if current in selected:
                    selected.discard(current)
                else:
                    selected.add(current)
            elif key in (curses.KEY_ENTER, 10, 13):
                return {items[i].id_readable for i in selected}

    return curses.wrapper(draw)


def _tkinter_demo_selection(finished: Sequence["SprintIssue"]) -> set[str]:
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    top = tk.Toplevel(root)
    top.title("sprint-recap — demo selection")

    tk.Label(top, text="Select resolved issues to demo:").pack(padx=8, pady=8)

    container = tk.Frame(top)
    container.pack(padx=8, pady=4, fill=tk.BOTH, expand=True)
    canvas = tk.Canvas(container)
    scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
    inner = tk.Frame(canvas)
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    vars_: list[tuple[str, tk.BooleanVar]] = []
    for issue in finished:
        var = tk.BooleanVar(value=False)
        tk.Checkbutton(inner, text=f"{issue.id_readable}  {issue.title}", variable=var, anchor="w").pack(
            fill=tk.X, padx=4, pady=1
        )
        vars_.append((issue.id_readable, var))

    result: dict[str, set[str] | None] = {"value": None}

    def confirm() -> None:
        result["value"] = {id_ for id_, var in vars_ if var.get()}
        top.destroy()

    def cancel() -> None:
        top.destroy()

    button_frame = tk.Frame(top)
    button_frame.pack(pady=4)
    tk.Button(button_frame, text="OK", command=confirm).pack(side=tk.LEFT, padx=4)
    tk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.LEFT, padx=4)

    top.protocol("WM_DELETE_WINDOW", cancel)
    top.grab_set()
    root.wait_window(top)
    root.destroy()

    if result["value"] is None:
        raise ValueError("User cancelled demo selection.")
    return result["value"]


def prompt_demo_selection(finished: Sequence["SprintIssue"]) -> set[str]:
    if not finished:
        return set()
    mode = detect_prompt_mode()
    if mode == "console":
        return _console_demo_selection(finished)
    return _tkinter_demo_selection(finished)
