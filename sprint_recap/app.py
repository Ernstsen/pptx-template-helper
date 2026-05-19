"""Orchestration: run one recap end-to-end.

Happy paths after Iteration 2:
    cwd → detect prompt mode → read token (FR-016 — surface via active
    prompt mode if missing) → init dual-sink logger → load settings; if
    missing, run `first_time_setup` against the live YouTrack instance
    and save sprint-recap.json atomically (no token; FR-006/FR-016) →
    find template → build YouTrack client → reuse boards from setup or
    fetch → pick most-recent sprint (latest by end date) → fetch issues
    → build agenda plan → derive output and log paths → attach file
    handler (replays buffered records) → render deck (handling FR-004
    overwrite prompt) → write cross-reference list → run footer.

On any error we log an ERROR line and abort *before* touching an
existing good output (FR-014) and *without* writing a settings file
(FR-005, FR-014). The token never appears in any logged or raised
string; the redaction filter is a defense-in-depth backstop.
"""

from __future__ import annotations

import argparse
import logging
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from sprint_recap import classify, config, deck, logging_setup, naming, prompts
from sprint_recap.models import AgendaBucket, AgendaPlan, SavedSettings, Sprint
from sprint_recap.youtrack import Board, Project, YouTrackClient, YouTrackError


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse CLI args. Iteration 3 introduces a single boolean flag.

    The default no-arg flow keeps the FR-007 latest-by-end-date sprint;
    ``--pick-sprint`` flips orchestration into the picker (US3).
    """
    parser = argparse.ArgumentParser(
        prog="sprint_recap",
        description="Generate the sprint recap deck for the configured board.",
    )
    parser.add_argument(
        "--pick-sprint",
        action="store_true",
        dest="pick_sprint",
        help="Pick a sprint from the configured board instead of the latest.",
    )
    return parser.parse_args(argv)


def _validate_youtrack_url(raw: str) -> str:
    url = raw.strip().rstrip("/")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"YouTrack URL must use http(s) and have a host: {raw!r}")
    return url


def _resolve_project(client: YouTrackClient, logger: logging.Logger) -> Project:
    """Loop the project prompt until exactly one visible project resolves
    or the user cancels (raises ValueError). Re-prompts on 0/many."""
    while True:
        query = prompts.prompt_text("Project (short name or full name, e.g. PROJ):")
        if not query:
            raise ValueError("First-time setup cancelled at project prompt.")
        logger.info("setup: project query = %r", query)
        matches = client.verify_project(query)
        if not matches:
            logger.warning("setup: no project matches %r — try again or cancel.", query)
            continue
        if len(matches) == 1:
            return matches[0]
        labels = [f"{p.short_name} — {p.name} (id={p.id})" for p in matches]
        chosen = prompts.prompt_choice(
            f"Multiple projects matched {query!r}; pick one:", labels
        )
        if chosen is None:
            raise ValueError("First-time setup cancelled at project disambiguation.")
        return matches[labels.index(chosen)]


def _resolve_board(
    client: YouTrackClient,
    project: Project,
    logger: logging.Logger,
) -> tuple[Board, list[Board]]:
    """Resolve the agile board for `project`. Defaults if there is exactly
    one; prompts if many; raises YouTrackError (FR-005 edge case) if zero.

    Returns (chosen_board, full_boards_response) so the orchestrator can
    reuse the agile-boards response without a second round-trip."""
    boards = client.list_agile_boards()
    matching = [b for b in boards if project.id in b.project_ids]
    if not matching:
        raise YouTrackError(
            f"No Agile boards visible for project {project.short_name!r} — "
            "ask an admin or check the token's permissions."
        )
    if len(matching) == 1:
        board = matching[0]
        logger.info("setup: board = %s (id=%s) [auto: only one]", board.name, board.id)
        return board, boards
    labels = [f"{b.name} (id={b.id})" for b in matching]
    chosen = prompts.prompt_choice("Pick the Agile board:", labels)
    if chosen is None:
        raise ValueError("First-time setup cancelled at board prompt.")
    board = matching[labels.index(chosen)]
    logger.info("setup: board = %s (id=%s)", board.name, board.id)
    return board, boards


def first_time_setup(
    working_folder: Path,
    token: str,
    *,
    logger: logging.Logger,
) -> tuple[SavedSettings, list[Board]]:
    """Walk the user through URL → project → board, verify against the
    live YouTrack instance, and save the non-token settings atomically.

    Returns the just-saved `SavedSettings` and the agile-boards response
    so the caller continues into the recap flow without a second
    round-trip (T027 / quickstart.md). On *any* error path settings are
    NOT persisted (FR-005, FR-014).
    """
    raw_url = prompts.prompt_text(
        "YouTrack URL (e.g. https://youtrack.example.com):"
    )
    if not raw_url:
        raise ValueError("First-time setup cancelled at YouTrack URL prompt.")
    url = _validate_youtrack_url(raw_url)
    logger.info("setup: youtrack_url = %s", url)

    client = YouTrackClient(url, token)
    project = _resolve_project(client, logger)
    logger.info(
        "setup: project = %s (id=%s, name=%r)",
        project.short_name,
        project.id,
        project.name,
    )

    board, boards = _resolve_board(client, project, logger)

    settings = SavedSettings(
        youtrack_url=url,
        project_id=project.id,
        project_short_name=project.short_name,
        board_id=board.id,
        board_name=board.name,
        last_sprint_id=None,
        issue_type_filter="all",
        schema_version=1,
    )
    config.save_settings(working_folder, settings)
    logger.info("setup: settings saved to %s", working_folder / "sprint-recap.json")
    return settings, boards


def _pick_default_sprint(boards: list[Board], settings: SavedSettings) -> Sprint:
    """Sprint with the latest end date on the configured board.

    Originally FR-007 was "most recently archived"; relaxed to "latest by
    end date" because teams don't always archive finished sprints in
    YouTrack, and the `Sprint` list is already filtered to dated sprints
    by the client.
    """
    board = next((b for b in boards if b.id == settings.board_id), None)
    if board is None:
        raise YouTrackError(
            f"Board {settings.board_name!r} (id={settings.board_id}) is no longer "
            "visible to this token. Re-run first-time setup or fix `sprint-recap.json`."
        )
    if not board.sprints:
        raise YouTrackError(
            f"Board {settings.board_name!r} has no dated sprints; nothing to recap."
        )
    return max(board.sprints, key=lambda s: s.end)


def _write_cross_reference(
    log: logging.Logger, plan: AgendaPlan
) -> None:
    log.info("agenda:")
    for issue in plan.demo:
        log.info("  %s | demo     | %s", issue.id_readable, issue.title)
    for issue in plan.no_demo:
        log.info("  %s | no-demo  | %s", issue.id_readable, issue.title)
    for issue in plan.open:
        log.info("  %s | open     | %s", issue.id_readable, issue.title)
    for issue in plan.excluded:
        log.info("  %s | excluded | %s", issue.id_readable, issue.title)


def _apply_categorization(
    plan: AgendaPlan, mapping: dict[str, AgendaBucket]
) -> AgendaPlan:
    """Rebuild the four bucket lists from a `id_readable → bucket` mapping.

    Order within each output bucket:
      * Finished issues (resolved_at is not None) come first, retaining
        their input `(resolved_at, id_readable)` order.
      * Unresolved issues come next, retaining their input
        `(created_at, id_readable)` order.
    The input plan's per-bucket order is taken as already-sorted; this
    helper only re-bucketises and re-merges, preserving relative order.

    Validates the spec 004 invariant
        len(demo) + len(no_demo) + len(open) + len(excluded)
        == filtered_count - collapsed_subtask_count
    and raises `ValueError` on any inconsistency. The prompt is the only
    producer of `mapping`, so a violation is a programmer error.
    """
    # Preserve the input plan's order: finished issues first (resolved_at
    # ascending), then unresolved (created_at ascending). The input plan
    # already has each bucket in its natural sort, so we can just take
    # the four lists in order and assume each "side" stays internally
    # ordered.
    all_issues = [*plan.demo, *plan.no_demo, *plan.open, *plan.excluded]

    by_id = {i.id_readable: i for i in all_issues}
    if set(mapping.keys()) != set(by_id.keys()):
        missing = set(by_id.keys()) - set(mapping.keys())
        extra = set(mapping.keys()) - set(by_id.keys())
        raise ValueError(
            f"categorization mapping mismatch: missing={sorted(missing)} "
            f"extra={sorted(extra)}"
        )

    finished = [i for i in all_issues if i.is_finished]
    unresolved = [i for i in all_issues if not i.is_finished]
    finished.sort(key=lambda i: (i.resolved_at, i.id_readable))
    unresolved.sort(key=lambda i: (i.created_at, i.id_readable))

    buckets: dict[str, list] = {
        "present": [],
        "mention": [],
        "open": [],
        "exclude": [],
    }
    for issue in finished:
        b = mapping[issue.id_readable]
        if b not in buckets:
            raise ValueError(
                f"invalid bucket {b!r} for {issue.id_readable!r}"
            )
        buckets[b].append(issue)
    for issue in unresolved:
        b = mapping[issue.id_readable]
        if b not in buckets:
            raise ValueError(
                f"invalid bucket {b!r} for {issue.id_readable!r}"
            )
        buckets[b].append(issue)

    new_plan = AgendaPlan(
        demo=buckets["present"],
        no_demo=buckets["mention"],
        open=buckets["open"],
        excluded=buckets["exclude"],
        unfiltered_count=plan.unfiltered_count,
        filtered_count=plan.filtered_count,
        collapsed_subtask_count=plan.collapsed_subtask_count,
    )

    total = (
        len(new_plan.demo)
        + len(new_plan.no_demo)
        + len(new_plan.open)
        + len(new_plan.excluded)
    )
    expected = new_plan.filtered_count - new_plan.collapsed_subtask_count
    if total != expected:
        raise ValueError(
            f"categorization invariant violated: "
            f"buckets sum to {total}, expected {expected} "
            f"(filtered={new_plan.filtered_count}, "
            f"collapsed={new_plan.collapsed_subtask_count})"
        )
    return new_plan


def _pick_sprint_interactively(
    boards: list[Board], settings: SavedSettings, logger: logging.Logger
) -> Sprint:
    """Run the US3 picker against the configured board's sprints. Raises
    ValueError if the user cancels — caller surfaces that as the standard
    cancel-aborts-without-writing-files path."""
    board = next((b for b in boards if b.id == settings.board_id), None)
    if board is None:
        raise YouTrackError(
            f"Board {settings.board_name!r} (id={settings.board_id}) is no longer "
            "visible to this token. Re-run first-time setup or fix `sprint-recap.json`."
        )
    if not board.sprints:
        raise YouTrackError(
            f"Board {settings.board_name!r} has no dated sprints; nothing to recap."
        )
    chosen = prompts.prompt_sprint(board.sprints)
    if chosen is None:
        raise ValueError("User cancelled at sprint picker; aborting.")
    logger.info(
        "sprint_picker = %s (id=%s) [user-selected]",
        chosen.name,
        chosen.id,
    )
    return chosen


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Returns 0 on success, 1 on error. Never raises out of main."""
    args = parse_args(argv)
    started = datetime.now()
    working_folder = Path.cwd()
    prompt_mode = prompts.detect_prompt_mode()

    # FR-016: read the token first so the redaction filter wraps every
    # log record from line one. If it's missing, surface the error in
    # whichever prompt mode is active and abort BEFORE any HTTP call and
    # BEFORE any settings write (FR-014).
    try:
        token = config.read_token()
    except EnvironmentError as e:
        prompts.show_error(str(e))
        return 1

    logger = logging_setup.init_logger(token=token)
    logger.info("── sprint-recap run start ──")
    logger.info("working_folder = %s", working_folder)
    logger.info("prompt_mode = %s", prompt_mode)

    try:
        settings = config.load_settings(working_folder)
        boards: Optional[list[Board]] = None
        if settings is None:
            logger.info("No sprint-recap.json found — running first-time setup.")
            settings, boards = first_time_setup(
                working_folder, token, logger=logger
            )

        logger.info(
            "youtrack_url = %s",
            settings.youtrack_url,
        )
        logger.info(
            "project = %s (id=%s)",
            settings.project_short_name,
            settings.project_id,
        )
        logger.info(
            "board = %s (id=%s)",
            settings.board_name,
            settings.board_id,
        )

        template_path = prompts.find_template(working_folder)

        client = YouTrackClient(settings.youtrack_url, token)
        if boards is None:
            boards = client.list_agile_boards()

        if args.pick_sprint:
            sprint = _pick_sprint_interactively(boards, settings, logger)
        else:
            sprint = _pick_default_sprint(boards, settings)

        logger.info(
            "sprint = %s (id=%s) %s → %s",
            sprint.name,
            sprint.id,
            sprint.start.isoformat(),
            sprint.end.isoformat(),
        )

        issues = client.fetch_sprint_issues(settings.board_id, sprint.id)
        logger.info("issues_retrieved = %d", len(issues))
        logger.info(
            "issue_type_filter = %s",
            (
                '"all"'
                if settings.issue_type_filter == "all"
                else settings.issue_type_filter
            ),
        )

        plan = classify.build_agenda_plan(issues, settings.issue_type_filter)
        logger.info("filtered_count = %d", plan.filtered_count)
        logger.info("collapsed_subtasks = %d", plan.collapsed_subtask_count)

        mapping = prompts.prompt_categorization(plan)
        if mapping:
            plan = _apply_categorization(plan, mapping)

        logger.info(
            "demo_count = %d   no_demo_count = %d   open_count = %d   excluded_count = %d",
            len(plan.demo),
            len(plan.no_demo),
            len(plan.open),
            len(plan.excluded),
        )

        output_path, log_path = naming.output_paths(
            working_folder=working_folder,
            template_path=template_path,
            sprint_name=sprint.name,
            sprint_end=sprint.end,
            idreadable_fallback=sprint.id,
        )
        logging_setup.attach_file_handler(log_path, token=token)

        if output_path.exists():
            choice = prompts.confirm_overwrite(output_path)
            logger.info("overwrite_prompt = %s", choice)
            if choice == "cancel":
                logger.error("User cancelled at overwrite prompt; aborting.")
                logger.info("── sprint-recap run end (error) ──")
                return 1
            if choice == "save_as":
                # Iteration-1 fallback per T018: re-prompt for an alternate
                # name inside the working folder. Keep it minimal.
                alt = input(
                    "Type an alternate filename (will be placed in the "
                    f"working folder; .pptx added if missing): "
                ).strip() if prompt_mode == "console" else ""
                if not alt:
                    logger.error("No alternate filename supplied; aborting.")
                    logger.info("── sprint-recap run end (error) ──")
                    return 1
                if not alt.endswith(".pptx"):
                    alt = alt + ".pptx"
                output_path = working_folder / alt

        deck.render_deck(template_path, output_path, sprint, plan)
        logger.info("output = %s", output_path)
        _write_cross_reference(logger, plan)
        logger.info("── sprint-recap run end (success) ──")
        return 0

    except (YouTrackError, EnvironmentError, FileNotFoundError, config.SettingsError, ValueError) as e:
        message = logging_setup.redact(str(e), token)
        logger.error("%s", message)
        logger.info("── sprint-recap run end (error) ──")
        return 1
    except Exception as e:  # noqa: BLE001  (last-line-of-defense)
        message = logging_setup.redact(str(e), token)
        logger.error("Unexpected error: %s", message)
        logger.info("── sprint-recap run end (error) ──")
        return 1
    finally:
        elapsed = (datetime.now() - started).total_seconds()
        logger.info("elapsed_seconds = %.2f", elapsed)


if __name__ == "__main__":
    sys.exit(main())
