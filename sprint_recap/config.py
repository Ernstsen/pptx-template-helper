"""Settings load and token reading.

`sprint-recap.json` schema and forbidden-key rules per
contracts/settings-file.md. The token is read from the environment per
FR-016 and is never persisted.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from sprint_recap.models import IssueTypeFilter, SavedSettings

SETTINGS_FILENAME = "sprint-recap.json"
SCHEMA_VERSION = 1

FORBIDDEN_KEYS = {"YOUTRACK_TOKEN", "token", "bearer", "password", "api_key"}

_log = logging.getLogger(__name__)


class SettingsError(Exception):
    """Raised when settings exist but are unusable (corrupt schema, forbidden
    keys, wrong version)."""


def load_settings(working_folder: Path) -> Optional[SavedSettings]:
    """Return the loaded SavedSettings, or None if the folder is
    un-configured (file missing / unreadable JSON / missing required
    keys). Raises SettingsError for corruption that the user must fix
    by hand (forbidden keys, unsupported schema version)."""
    path = working_folder / SETTINGS_FILENAME
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Treat un-parseable file as un-configured (US2 trigger).
        _log.warning("%s exists but is not valid JSON; treating folder as un-configured", path)
        return None
    if not isinstance(raw, dict):
        raise SettingsError(f"{path}: top-level JSON must be an object")

    forbidden = FORBIDDEN_KEYS.intersection(raw.keys())
    if forbidden:
        raise SettingsError(
            f"{path}: forbidden field(s) present: {sorted(forbidden)}. "
            "Remove them by hand and re-run."
        )

    schema_version = raw.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise SettingsError(
            f"{path}: unsupported schema_version {schema_version!r}; "
            f"expected {SCHEMA_VERSION}. Delete the file and re-run first-time setup."
        )

    required = ("youtrack_url", "project_id", "project_short_name", "board_id", "board_name")
    missing = [k for k in required if k not in raw]
    if missing:
        raise SettingsError(
            f"{path}: missing required field(s) {missing}. "
            "Delete the file and re-run first-time setup."
        )

    raw_filter = raw.get("issue_type_filter", "all")
    issue_type_filter: IssueTypeFilter
    if raw_filter == "all":
        issue_type_filter = "all"
    elif isinstance(raw_filter, list) and all(isinstance(x, str) for x in raw_filter):
        if len(raw_filter) == 0:
            _log.warning(
                "%s: issue_type_filter is an empty list; treating as \"all\"", path
            )
            issue_type_filter = "all"
        else:
            issue_type_filter = list(raw_filter)
    else:
        raise SettingsError(
            f"{path}: issue_type_filter must be \"all\" or a list of strings"
        )

    return SavedSettings(
        youtrack_url=str(raw["youtrack_url"]).rstrip("/"),
        project_id=str(raw["project_id"]),
        project_short_name=str(raw["project_short_name"]),
        board_id=str(raw["board_id"]),
        board_name=str(raw["board_name"]),
        last_sprint_id=raw.get("last_sprint_id"),
        issue_type_filter=issue_type_filter,
        schema_version=SCHEMA_VERSION,
    )


def read_token() -> str:
    """Read YOUTRACK_TOKEN from the environment. Raises with explicit
    guidance per FR-016 if it is missing or empty."""
    value = os.environ.get("YOUTRACK_TOKEN", "").strip()
    if not value:
        raise EnvironmentError("YOUTRACK_TOKEN not set — see README.md")
    return value
