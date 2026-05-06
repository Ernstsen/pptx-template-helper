"""Unit tests for sprint-recap.json save/load (T021).

Covers contracts/settings-file.md:
- atomic .tmp + os.replace write
- never persists YOUTRACK_TOKEN or any forbidden-key field
- rejects schema_version != 1 on load
- treats issue_type_filter == [] as "all" with a logged WARN
- a process killed mid-write must NOT leave a half-written
  sprint-recap.json (we simulate by writing only the .tmp and asserting
  the target file is absent or holds prior good content)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from sprint_recap import config
from sprint_recap.config import SETTINGS_FILENAME, SettingsError, load_settings, save_settings
from sprint_recap.models import SavedSettings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(folder: Path, payload: dict) -> Path:
    path = folder / SETTINGS_FILENAME
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _good_settings() -> SavedSettings:
    return SavedSettings(
        youtrack_url="https://yt.example.com",
        project_id="0-7",
        project_short_name="PROJ",
        board_id="121-3",
        board_name="PROJ Scrum",
        last_sprint_id=None,
        issue_type_filter="all",
        schema_version=1,
    )


# ---------------------------------------------------------------------------
# save_settings
# ---------------------------------------------------------------------------


def test_save_settings_writes_expected_json(tmp_path: Path) -> None:
    save_settings(tmp_path, _good_settings())
    target = tmp_path / SETTINGS_FILENAME
    assert target.exists()
    raw = json.loads(target.read_text(encoding="utf-8"))
    assert raw == {
        "schema_version": 1,
        "youtrack_url": "https://yt.example.com",
        "project_id": "0-7",
        "project_short_name": "PROJ",
        "board_id": "121-3",
        "board_name": "PROJ Scrum",
        "last_sprint_id": None,
        "issue_type_filter": "all",
    }


def test_save_settings_uses_indent_sort_keys_unicode(tmp_path: Path) -> None:
    settings = _good_settings()
    settings.board_name = "Équipe Été"  # non-ASCII to verify ensure_ascii=False
    save_settings(tmp_path, settings)
    text = (tmp_path / SETTINGS_FILENAME).read_text(encoding="utf-8")
    # indent=2: two-space indent on at least one nested key
    assert "\n  " in text
    # sort_keys=True: 'board_id' precedes 'board_name', 'project_id' precedes 'project_short_name'
    bi = text.index("board_id")
    bn = text.index("board_name")
    pi = text.index("project_id")
    ps = text.index("project_short_name")
    assert bi < bn
    assert pi < ps
    # ensure_ascii=False: literal unicode survives, not escaped
    assert "Équipe Été" in text


def test_save_settings_trims_trailing_slash_on_url(tmp_path: Path) -> None:
    settings = _good_settings()
    settings.youtrack_url = "https://yt.example.com/"
    save_settings(tmp_path, settings)
    raw = json.loads((tmp_path / SETTINGS_FILENAME).read_text(encoding="utf-8"))
    assert raw["youtrack_url"] == "https://yt.example.com"


def test_save_settings_atomic_via_tmp_then_replace(tmp_path: Path, monkeypatch) -> None:
    """The persisted file must appear via os.replace from a sibling .tmp."""
    target = tmp_path / SETTINGS_FILENAME
    tmp = tmp_path / (SETTINGS_FILENAME + ".tmp")
    seen: dict[str, bool] = {"tmp_existed_pre_replace": False}

    real_replace = config.os.replace

    def spy_replace(src, dst):
        if str(src) == str(tmp) and Path(src).exists():
            seen["tmp_existed_pre_replace"] = True
        return real_replace(src, dst)

    monkeypatch.setattr(config.os, "replace", spy_replace)
    save_settings(tmp_path, _good_settings())
    assert target.exists()
    assert not tmp.exists()
    assert seen["tmp_existed_pre_replace"], "save_settings must write via .tmp first"


def test_save_settings_overwrites_prior_good_file_atomically(tmp_path: Path) -> None:
    target = tmp_path / SETTINGS_FILENAME
    target.write_text(
        json.dumps({"schema_version": 1, "stale": True}),
        encoding="utf-8",
    )
    save_settings(tmp_path, _good_settings())
    raw = json.loads(target.read_text(encoding="utf-8"))
    assert "stale" not in raw
    assert raw["youtrack_url"] == "https://yt.example.com"


def test_save_settings_killed_mid_write_leaves_target_unchanged(
    tmp_path: Path, monkeypatch
) -> None:
    """If os.replace fails (simulating a kill mid-write), the prior good
    target file is unchanged and the .tmp may or may not linger — but the
    target file is NEVER half-written."""
    target = tmp_path / SETTINGS_FILENAME
    target.write_text(
        json.dumps({"schema_version": 1, "good": True}),
        encoding="utf-8",
    )
    prior_bytes = target.read_bytes()

    def boom(src, dst):  # noqa: ARG001
        raise OSError("simulated kill")

    monkeypatch.setattr(config.os, "replace", boom)
    with pytest.raises(OSError):
        save_settings(tmp_path, _good_settings())
    # Target file is byte-identical to the prior good content.
    assert target.read_bytes() == prior_bytes


def test_save_settings_rejects_token_field_in_payload(tmp_path: Path) -> None:
    """save_settings must NEVER persist YOUTRACK_TOKEN or any forbidden
    field, even if the caller smuggles one onto SavedSettings via setattr."""
    settings = _good_settings()
    setattr(settings, "YOUTRACK_TOKEN", "perm:secret")
    setattr(settings, "token", "perm:secret")
    setattr(settings, "bearer", "perm:secret")
    save_settings(tmp_path, settings)
    raw = (tmp_path / SETTINGS_FILENAME).read_text(encoding="utf-8")
    for forbidden in ("YOUTRACK_TOKEN", "perm:secret", "bearer", "password", "api_key"):
        assert forbidden not in raw, f"forbidden token leaked into settings: {forbidden!r}"


# ---------------------------------------------------------------------------
# load_settings — schema/version rules
# ---------------------------------------------------------------------------


def test_load_settings_missing_returns_none(tmp_path: Path) -> None:
    assert load_settings(tmp_path) is None


def test_load_settings_invalid_json_returns_none_for_us2_trigger(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    (tmp_path / SETTINGS_FILENAME).write_text("{not-json", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        result = load_settings(tmp_path)
    assert result is None


def test_load_settings_rejects_unknown_schema_version(tmp_path: Path) -> None:
    _write(tmp_path, {"schema_version": 2, "youtrack_url": "https://x"})
    with pytest.raises(SettingsError) as excinfo:
        load_settings(tmp_path)
    assert "schema_version" in str(excinfo.value)


def test_load_settings_rejects_forbidden_keys(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "schema_version": 1,
            "youtrack_url": "https://x",
            "project_id": "0-7",
            "project_short_name": "PROJ",
            "board_id": "121-3",
            "board_name": "P",
            "issue_type_filter": "all",
            "YOUTRACK_TOKEN": "leaked",
        },
    )
    with pytest.raises(SettingsError) as excinfo:
        load_settings(tmp_path)
    assert "YOUTRACK_TOKEN" in str(excinfo.value)


def test_load_settings_empty_filter_is_all_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _write(
        tmp_path,
        {
            "schema_version": 1,
            "youtrack_url": "https://x",
            "project_id": "0-7",
            "project_short_name": "PROJ",
            "board_id": "121-3",
            "board_name": "P",
            "issue_type_filter": [],
        },
    )
    with caplog.at_level(logging.WARNING, logger="sprint_recap.config"):
        settings = load_settings(tmp_path)
    assert settings is not None
    assert settings.issue_type_filter == "all"
    assert any("issue_type_filter" in rec.getMessage() for rec in caplog.records)


def test_load_settings_round_trips_what_save_writes(tmp_path: Path) -> None:
    save_settings(tmp_path, _good_settings())
    loaded = load_settings(tmp_path)
    assert loaded is not None
    assert loaded.youtrack_url == "https://yt.example.com"
    assert loaded.project_id == "0-7"
    assert loaded.project_short_name == "PROJ"
    assert loaded.board_id == "121-3"
    assert loaded.board_name == "PROJ Scrum"
    assert loaded.issue_type_filter == "all"
    assert loaded.last_sprint_id is None
    assert loaded.schema_version == 1
