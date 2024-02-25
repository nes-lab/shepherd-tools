"""shepherd.datalib
~~~~~
Provides classes for storing and retrieving sampled IV data to/from
HDF5 files.

"""
from shepherd_core import Writer

from .reader import Reader

__version__ = "2024.02.0"

__all__ = [
    "Reader",
    "Writer",
]
