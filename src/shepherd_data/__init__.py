"""
shepherd.datalib
~~~~~
Provides classes for storing and retrieving sampled IV data to/from
HDF5 files.

"""
import logging

from .reader import Reader
from .writer import Writer

__version__ = "2022.9.3"
__all__ = [
    "Reader",
    "Writer",
]

logging.basicConfig(format="%(name)s %(levelname)s: %(message)s", level=logging.INFO)
