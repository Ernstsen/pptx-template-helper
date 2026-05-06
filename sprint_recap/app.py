"""Orchestration: run one recap end-to-end.

Iteration-1 happy path:
    cwd → init logger (console only) → read token → load settings (must
    exist; missing → friendly error pointing at the contract) → find
    template → build YouTrack client → fetch boards → pick most-recently
    sprint (latest by end date) → fetch issues → build agenda plan → derive
    output and log paths → attach file handler (replays buffered records)
    → render deck (handling FR-004 overwrite prompt) → write
    cross-reference list → run footer.

On any error we log an ERROR line and abort *before* touching an
existing good output (FR-014). The token never appears in any logged or
raised string; the redaction filter is a defense-in-depth backstop.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from sprint_recap import classify, config, deck, logging_setup, naming, prompts
from sprint_recap.models import AgendaPlan, SavedSettings, Sprint
from sprint_recap.youtrack import Board, YouTrackClient, YouTrackError


def _setup_message(working_folder: Path) -> str:
    return (
        f"No `sprint-recap.json` found in {working_folder}. Either create "
        "one matching `specs/001-sprint-recap-deck/contracts/settings-file.md` "
        "or wait for first-time setup (Iteration 2)."
    )


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
    for issue in plan.finished:
        log.info("  %s | finished | %s", issue.id_readable, issue.title)
    for issue in plan.open:
        log.info("  %s | open     | %s", issue.id_readable, issue.title)


def main() -> int:
    """Returns 0 on success, 1 on error. Never raises out of main."""
    started = datetime.now()
    working_folder = Path.cwd()
    prompt_mode = prompts.detect_prompt_mode()

    # Read the token *before* configuring the logger so the redaction filter
    # is wired from the first record. If the token is missing we cannot log
    # to a file (no output stem yet) — surface the FR-016 error on stderr
    # and return.
    try:
        token = config.read_token()
    except EnvironmentError as e:
        sys.stderr.write(f"{e}\n")
        return 1

    logger = logging_setup.init_logger(token=token)
    logger.info("── sprint-recap run start ──")
    logger.info("working_folder = %s", working_folder)
    logger.info("prompt_mode = %s", prompt_mode)

    try:
        settings = config.load_settings(working_folder)
        if settings is None:
            raise EnvironmentError(_setup_message(working_folder))

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
        boards = client.list_agile_boards()
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
        logger.info(
            "finished_count = %d   open_count = %d",
            len(plan.finished),
            len(plan.open),
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
