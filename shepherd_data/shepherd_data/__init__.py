"""Provides higher functionality compared to core, with additional lib-requirements.

Provides classes for storing and retrieving sampled IV data to/from
HDF5 files, with
- resampling
- plotting
- extracting metadata
"""

from shepherd_core import Writer

from .reader import Reader

__version__ = "2024.5.1"

__all__ = [
    "Reader",
    "Writer",
]
