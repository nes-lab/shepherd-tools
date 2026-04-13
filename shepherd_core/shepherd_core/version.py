"""Separated string avoids circular imports."""
from importlib import metadata

core_version: str = metadata.version("shepherd-core")
