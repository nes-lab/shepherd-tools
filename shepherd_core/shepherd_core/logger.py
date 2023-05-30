import logging

import chromalog
from pydantic import validate_arguments

chromalog.basicConfig(format="%(message)s")
logger = logging.getLogger("SHPCore")
logger.addHandler(logging.NullHandler())

verbose_level: int = 2


def get_verbose_level() -> int:
    return verbose_level


@validate_arguments
def set_verbose_level(verbose: int) -> None:
    global verbose_level
    verbose_level = min(max(verbose, 0), 3)

    if verbose_level == 0:
        logger.setLevel(logging.ERROR)
        logging.basicConfig(level=logging.ERROR)
    elif verbose_level == 1:
        logger.setLevel(logging.WARNING)
    elif verbose_level == 2:
        logger.setLevel(logging.INFO)
    elif verbose_level > 2:
        logger.setLevel(logging.DEBUG)

    if verbose_level < 3:
        # reduce log-overhead when not debugging, also more user-friendly exceptions
        logging._srcfile = None
        logging.logThreads = 0
        logging.logProcesses = 0

    if verbose_level > 2:
        chromalog.basicConfig(format="%(name)s %(levelname)s: %(message)s")
    else:
        chromalog.basicConfig(format="%(message)s")  # reduce internals


set_verbose_level(2)

# short reminder for format-strings:
# %s    string
# %d    decimal
# %f    float
# %o    decimal as octal
# %x    decimal as hex
#
# %05d  pad right (aligned with 5chars)
# %-05d pad left (left aligned)
# %06.2f    6chars float, including dec point, with 2 chars after
# %.5s  truncate to 5 chars
