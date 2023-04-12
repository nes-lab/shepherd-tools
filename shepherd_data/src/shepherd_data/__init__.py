"""
shepherd.datalib
~~~~~
Provides classes for storing and retrieving sampled IV data to/from
HDF5 files.

"""
import logging

from .reader import Reader
from shepherd_core import BaseWriter as Writer

__version__ = "2023.4.1"

__all__ = [
    "Reader",
    "Writer",
]
