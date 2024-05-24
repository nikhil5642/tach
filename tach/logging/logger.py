from __future__ import annotations

import logging
import multiprocessing
import os
import signal
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from tach import cache
from tach.logging.api import log_record, log_uid
from tach.parsing import parse_project_config

if TYPE_CHECKING:
    from types import FrameType


class LogDataModel(BaseModel):
    function: str
    parameters: dict[str, Any] = Field(default_factory=dict)


def send_log_entry(record: logging.LogRecord, entry: str) -> None:
    is_ci = "CI" in os.environ
    is_gauge = "IS_GAUGE" in os.environ
    data: Optional[LogDataModel] = getattr(record, "data", None)
    uid = cache.get_uid()
    log_data: dict[str, Any] = {
        "user": str(uid) if uid else None,
        "message": entry,
        "level": record.levelname,
        "timestamp": record.created,
        "function": data.function if data else None,
        "parameters": data.parameters if data else None,
    }
    if uid is not None:
        log_uid(uid=uid, is_ci=is_ci, is_gauge=is_gauge)
    log_record(record_data=log_data)


def handle_log_entry(record: logging.LogRecord, entry: str) -> None:
    # return on main process
    try:
        if os.fork() != 0:
            return
    except OSError:  # TODO WIN support
        return

    import sys

    devnull = open(os.devnull, "w")
    sys.stdout = devnull
    sys.stderr = devnull

    def handler(signum: int, frame: Optional[FrameType]) -> None:
        raise TimeoutError()

    signal.signal(signal.SIGALRM, handler)  # ensure logging process always exits
    signal.alarm(3)  # 3 sec timeout
    try:
        send_log_entry(record=record, entry=entry)
    except Exception:  # noqa
        pass
    finally:
        signal.alarm(0)


class RemoteLoggingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        log_entry = self.format(record)
        # Ensure logs are nonblocking to main process
        process = multiprocessing.Process(
            target=handle_log_entry, args=(record, log_entry)
        )
        process.start()
        process.join()


logger = logging.getLogger("tach")
logger.setLevel(logging.INFO)
remote_handler = RemoteLoggingHandler()

# Check if logging is enabled
disable_logging = False
try:
    project_config = parse_project_config()
    disable_logging = project_config.disable_logging
except SystemExit:
    pass
if not disable_logging:
    logger.addHandler(remote_handler)
else:
    logger.disabled = True
