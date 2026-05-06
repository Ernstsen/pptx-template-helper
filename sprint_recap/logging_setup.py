"""Per-run dual-sink logger (file + console) per FR-017 / research §R6.

The output stem (and therefore the log filename) is only known after the
sprint dates are resolved. So `init_logger()` first attaches a stdout
StreamHandler and an in-memory MemoryHandler buffer; once the stem is
known the orchestrator calls `attach_file_handler(log_path)`, which
opens the file, replays buffered records, and switches the buffer's
target so subsequent records flush live.

Token redaction (research §R7): the redaction filter strips any
occurrence of the token from emitted messages. This is defense in
depth — the calling code is also expected not to log the token.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

LOGGER_NAME = "sprint_recap"
LOG_FORMAT = "%(asctime)s %(levelname)-5s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _RedactionFilter(logging.Filter):
    """Replace the token in any record message with `***`. Defense in
    depth — calling code should not log the token in the first place."""

    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token

    def filter(self, record: logging.LogRecord) -> bool:
        if self._token and isinstance(record.msg, str) and self._token in record.msg:
            record.msg = record.msg.replace(self._token, "***")
        if record.args:
            record.args = tuple(
                a.replace(self._token, "***") if isinstance(a, str) and self._token else a
                for a in (record.args if isinstance(record.args, tuple) else (record.args,))
            )
        return True


_BUFFER_HANDLER: logging.handlers.MemoryHandler | None = None
_FILE_HANDLER: logging.FileHandler | None = None


def init_logger(token: str | None = None) -> logging.Logger:
    """Configure the root sprint_recap logger with a stdout handler and an
    in-memory buffer. Idempotent — repeated calls reset the configuration
    so the test suite can re-init between cases."""
    global _BUFFER_HANDLER, _FILE_HANDLER

    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    # MemoryHandler buffers records until a target is set or it's flushed.
    # capacity=10_000 is far above any realistic per-run record count.
    buffer = logging.handlers.MemoryHandler(
        capacity=10_000, flushLevel=logging.CRITICAL + 1
    )
    buffer.setFormatter(formatter)

    if token:
        redaction = _RedactionFilter(token)
        console.addFilter(redaction)
        buffer.addFilter(redaction)

    logger.addHandler(console)
    logger.addHandler(buffer)

    _BUFFER_HANDLER = buffer
    _FILE_HANDLER = None
    return logger


def attach_file_handler(log_path: Path, token: str | None = None) -> None:
    """Open `log_path`, replay any buffered records into it, then attach
    it as a live handler so subsequent log lines write through directly."""
    global _BUFFER_HANDLER, _FILE_HANDLER

    logger = logging.getLogger(LOGGER_NAME)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    file_handler = logging.FileHandler(str(log_path), mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    if token:
        file_handler.addFilter(_RedactionFilter(token))

    if _BUFFER_HANDLER is not None:
        _BUFFER_HANDLER.setTarget(file_handler)
        _BUFFER_HANDLER.flush()
        logger.removeHandler(_BUFFER_HANDLER)
        _BUFFER_HANDLER.close()
        _BUFFER_HANDLER = None

    logger.addHandler(file_handler)
    _FILE_HANDLER = file_handler


def redact(message: str, token: str | None) -> str:
    """Strip the token from `message`. Used by the orchestrator before
    raising or surfacing user-visible errors."""
    if not token:
        return message
    return message.replace(token, "***")
