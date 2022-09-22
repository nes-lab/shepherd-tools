"""
shepherd.datalib
~~~~~
Provides classes for storing and retrieving sampled IV data to/from
HDF5 files.

"""
import logging
from .reader import Reader
from .writer import Writer

# from .ivonne import Reader as IVonneReader

__version__ = "2022.9.1"
__all__ = [
    "Reader",
    "Writer",
]

logging.basicConfig(format="%(name)s %(levelname)s: %(message)s", level=logging.INFO)
