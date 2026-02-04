"""Generalized exit handler for Shepherd."""

import signal
import sys
from collections.abc import Callable
from types import FrameType

from .logger import log


def exit_gracefully(_signum: int, _frame: FrameType | None) -> None:
    """Usual exit handler for single-processing applications."""
    log.warning("Exiting!")
    sys.exit(0)


def activate_exit_handler(custom: Callable = exit_gracefully) -> None:
    """Register the provided exit handler or use the default one."""
    signal.signal(signal.SIGTERM, custom)
    signal.signal(signal.SIGINT, custom)
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, custom)
