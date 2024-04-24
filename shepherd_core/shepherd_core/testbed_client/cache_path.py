"""Generalized path for the file-cache."""

import os
from pathlib import Path


def _get_xdg_path(variable_name: str, default_path: Path) -> Path:
    _value = os.environ.get(variable_name)
    if _value is None or _value == "":
        return default_path
    return Path(_value)


user_path = Path("~").expanduser()

cache_xdg_path = _get_xdg_path("XDG_CACHE_HOME", user_path / ".cache")
cache_user_path = cache_xdg_path / "shepherd_datalib"
