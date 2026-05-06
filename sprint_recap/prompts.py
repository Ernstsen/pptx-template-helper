"""Console + tkinter prompt facade.

Mode is detected once at startup via `sys.stdin.isatty()` per FR-012 and
research §R3, and is held constant for the run. Iteration 1 covers
template discovery and the overwrite confirmation; first-time-setup
prompts and the sprint picker arrive in later iterations and reuse the
same facade.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Literal, Optional, Sequence

_log = logging.getLogger(__name__)

PromptMode = Literal["console", "tkinter"]
OverwriteChoice = Literal["overwrite", "save_as", "cancel"]

_PROMPT_MODE: Optional[PromptMode] = None


def detect_prompt_mode() -> PromptMode:
    """Compute the prompt mode once and cache it (FR-012)."""
    global _PROMPT_MODE
    if _PROMPT_MODE is None:
        _PROMPT_MODE = "console" if sys.stdin.isatty() else "tkinter"
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
