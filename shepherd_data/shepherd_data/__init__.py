"""
shepherd.datalib
~~~~~
Provides classes for storing and retrieving sampled IV data to/from
HDF5 files.

"""
from shepherd_core import BaseWriter as Writer

from .reader import Reader

__version__ = "2023.5.5"

__all__ = [
    "Reader",
    "Writer",
]
