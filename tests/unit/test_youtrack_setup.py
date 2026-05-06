"""Unit tests for YouTrack client setup-flow methods (T023).

Stubs `http_get` with recorded fixtures under tests/fixtures/youtrack/.
Validates the verify_project / list_agile_boards endpoints from
contracts/youtrack-api.md §1–§2 and the exact error-mapping strings
from "Error mapping".
"""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from typing import Callable

import pytest

from sprint_recap.youtrack import YouTrackClient, YouTrackError

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "youtrack"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _make_client(stub: Callable[[str, dict[str, str]], tuple[int, bytes]]) -> YouTrackClient:
    return YouTrackClient(
        base_url="https://yt.example.com",
        token="perm:redacted",
        http_get=stub,
    )


# ---------------------------------------------------------------------------
# URL hygiene (research §R2a)
# ---------------------------------------------------------------------------


def test_client_trims_trailing_slash_on_base_url() -> None:
    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        # The constructed URL must NOT contain a double-slash before /api.
        assert "://yt.example.com/api" in url
        assert "://yt.example.com//api" not in url
        return 200, b"[]"

    client = YouTrackClient(
        base_url="https://yt.example.com/", token="perm:t", http_get=stub
    )
    assert client.base_url == "https://yt.example.com"
    client.verify_project("PROJ")


def test_client_rejects_non_http_scheme() -> None:
    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        return 200, b"[]"

    with pytest.raises(YouTrackError):
        YouTrackClient(base_url="ftp://yt.example.com", token="t", http_get=stub)


def test_client_sends_authorization_and_accept_headers() -> None:
    seen: dict[str, dict[str, str]] = {}

    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        seen["headers"] = headers
        return 200, b"[]"

    client = _make_client(stub)
    client.verify_project("PROJ")
    assert seen["headers"]["Authorization"] == "Bearer perm:redacted"
    assert seen["headers"]["Accept"] == "application/json"


# ---------------------------------------------------------------------------
# verify_project
# ---------------------------------------------------------------------------


def test_verify_project_one_match() -> None:
    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        assert "/api/admin/projects" in url
        assert "query=PROJ" in url
        return 200, _load("projects_one.json")

    client = _make_client(stub)
    projects = client.verify_project("PROJ")
    assert len(projects) == 1
    assert projects[0].id == "0-7"
    assert projects[0].short_name == "PROJ"


def test_verify_project_many_matches_returned_for_disambiguation() -> None:
    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        return 200, _load("projects_many.json")

    client = _make_client(stub)
    projects = client.verify_project("PROJ")
    assert [p.short_name for p in projects] == ["PROJ", "PROJ-BE"]


def test_verify_project_zero_matches_returns_empty_list() -> None:
    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        return 200, _load("projects_zero.json")

    client = _make_client(stub)
    assert client.verify_project("PROJ") == []


def test_verify_project_404_maps_to_project_not_visible() -> None:
    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        return 404, b"not found"

    client = _make_client(stub)
    with pytest.raises(YouTrackError) as exc:
        client.verify_project("PROJ")
    assert str(exc.value) == "Project not visible to this token"


# ---------------------------------------------------------------------------
# list_agile_boards
# ---------------------------------------------------------------------------


def test_list_agile_boards_one_board_returns_full_metadata() -> None:
    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        assert "/api/agiles" in url
        return 200, _load("agiles_one_board.json")

    client = _make_client(stub)
    boards = client.list_agile_boards()
    assert len(boards) == 1
    assert boards[0].id == "121-3"
    assert boards[0].name == "PROJ Scrum"
    assert boards[0].project_ids == ["0-7"]
    assert len(boards[0].sprints) == 1
    assert boards[0].sprints[0].name == "Sprint 42"


def test_list_agile_boards_many_returns_all_for_caller_to_filter() -> None:
    """Per the contract, the program filters client-side by project id."""

    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        return 200, _load("agiles_many_boards.json")

    client = _make_client(stub)
    boards = client.list_agile_boards()
    assert {b.id for b in boards} == {"121-3", "121-4", "121-5"}
    proj_07 = [b for b in boards if "0-7" in b.project_ids]
    assert {b.name for b in proj_07} == {"PROJ Scrum", "PROJ Kanban"}


def test_list_agile_boards_zero_for_project_is_caller_responsibility() -> None:
    """The client returns whatever boards exist; the FR-005 'no Agile
    boards visible' edge case is detected by the caller."""

    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        return 200, _load("agiles_zero_boards_for_project.json")

    client = _make_client(stub)
    boards = client.list_agile_boards()
    matching = [b for b in boards if "0-7" in b.project_ids]
    assert matching == []


def test_list_agile_boards_skips_sprints_without_dates() -> None:
    payload = json.dumps(
        [
            {
                "id": "121-3",
                "name": "PROJ Scrum",
                "projects": [{"id": "0-7", "shortName": "PROJ"}],
                "sprints": [
                    {"id": "s1", "name": "Dated", "start": 1743984000000, "finish": 1746489600000, "archived": False},
                    {"id": "s2", "name": "NoDates", "start": None, "finish": None, "archived": False},
                ],
            }
        ]
    ).encode("utf-8")

    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        return 200, payload

    client = _make_client(stub)
    boards = client.list_agile_boards()
    assert [s.name for s in boards[0].sprints] == ["Dated"]


def test_list_agile_boards_404_maps_to_board_not_visible() -> None:
    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        return 404, b"not found"

    client = _make_client(stub)
    with pytest.raises(YouTrackError) as exc:
        client.list_agile_boards()
    assert str(exc.value) == "Board not visible to this token"


# ---------------------------------------------------------------------------
# Error mapping (contracts/youtrack-api.md "Error mapping")
# ---------------------------------------------------------------------------


def test_urlerror_maps_to_unreachable_message() -> None:
    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        raise urllib.error.URLError("dns failure")

    client = _make_client(stub)
    with pytest.raises(YouTrackError) as exc:
        client.verify_project("PROJ")
    assert str(exc.value) == "Could not reach YouTrack at https://yt.example.com"


@pytest.mark.parametrize("status", [401, 403])
def test_401_403_map_to_token_rejected(status: int) -> None:
    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        return status, b"unauthorized"

    client = _make_client(stub)
    with pytest.raises(YouTrackError) as exc:
        client.verify_project("PROJ")
    assert str(exc.value) == "Token rejected — check YOUTRACK_TOKEN"


def test_400_other_maps_to_rejected_request_with_short_body() -> None:
    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        return 400, b"bad query"

    client = _make_client(stub)
    with pytest.raises(YouTrackError) as exc:
        client.verify_project("PROJ")
    msg = str(exc.value)
    assert msg.startswith("YouTrack rejected the request: 400 — ")
    assert "bad query" in msg


def test_500_maps_to_server_error_try_again_later() -> None:
    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        return 503, b"down"

    client = _make_client(stub)
    with pytest.raises(YouTrackError) as exc:
        client.verify_project("PROJ")
    assert str(exc.value) == "YouTrack server error 503 — try again later"


def test_non_json_body_maps_to_unexpected_response() -> None:
    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        return 200, b"<html>not json</html>"

    client = _make_client(stub)
    with pytest.raises(YouTrackError) as exc:
        client.verify_project("PROJ")
    assert str(exc.value) == (
        "Unexpected response from YouTrack — is the URL pointing at the YouTrack API?"
    )


def test_token_never_appears_in_any_youtrack_error_message() -> None:
    def stub(url: str, headers: dict[str, str]) -> tuple[int, bytes]:
        return 401, b"bearer perm:redacted"

    client = _make_client(stub)
    with pytest.raises(YouTrackError) as exc:
        client.verify_project("PROJ")
    assert "perm:redacted" not in str(exc.value)
