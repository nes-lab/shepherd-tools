"""
shepherd.datalib
~~~~~
Provides classes for storing and retrieving sampled IV data to/from
HDF5 files.

"""
import shepherd_core
from shepherd_core import BaseWriter as Writer

from .reader import Reader

__version__ = shepherd_core.__version__  # Packages are released together

__all__ = [
    "Reader",
    "Writer",
]
