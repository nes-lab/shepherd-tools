"""Access-Classe for an optimized format.

This is only needed internally by the testbed.
It directly precomputes the memory-layout between userspace & PRU.

TODO:
- prototype to explore performance-gains
- add converter for whole directories
"""

from .reader import Reader
from .writer import Writer

__all__ = ["Reader", "Writer"]
