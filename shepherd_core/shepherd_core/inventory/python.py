"""Python related inventory model."""

import platform
from contextlib import suppress
from importlib import import_module
from typing import Optional

from pydantic import ConfigDict
from typing_extensions import Self

from ..data_models import ShpModel


class PythonInventory(ShpModel):
    """Python related inventory model."""

    # program versions
    h5py: Optional[str] = None
    numpy: Optional[str] = None
    pydantic: Optional[str] = None
    python: Optional[str] = None
    shepherd_core: Optional[str] = None
    shepherd_sheep: Optional[str] = None
    yaml: Optional[str] = None
    zstandard: Optional[str] = None

    model_config = ConfigDict(str_min_length=0)

    @classmethod
    def collect(cls) -> Self:
        model_dict = {"python": platform.python_version()}
        module_names = [
            "h5py",
            "numpy",
            "pydantic",
            "shepherd_core",
            "shepherd_sheep",
            "yaml",
            "zstandard",
        ]

        for module_name in module_names:
            with suppress(ImportError):
                module = import_module(module_name)
                model_dict[module_name] = module.__version__
                globals()

        return cls(**model_dict)
