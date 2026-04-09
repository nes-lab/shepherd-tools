"""Bundled core features used by several systems.

Provides classes for storing and retrieving sampled IV data to/from
HDF5 files.

"""

from .data_models.base.timezone import local_now
from .data_models.base.timezone import local_tz
from .data_models.task.emulation import Compression
from .inventory import Inventory
from .logger import get_verbose_level
from .logger import increase_verbose_level
from .logger import log
from .reader import Reader
from .version import version
from .writer import Writer

__version__ = version

__all__ = [
    "Compression",
    "Inventory",
    "Reader",
    "Writer",
    "get_verbose_level",
    "increase_verbose_level",
    "local_now",
    "local_tz",
    "log",
]
