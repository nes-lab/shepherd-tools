"""Python related inventory model."""

import platform
from contextlib import suppress
from importlib import import_module

from pydantic import ConfigDict
from typing_extensions import Self

from shepherd_core.data_models import ShpModel


class PythonInventory(ShpModel):
    """Python related inventory model."""

    # program versions
    h5py: str | None = None
    numpy: str | None = None
    pydantic: str | None = None
    python: str | None = None
    shepherd_core: str | None = None
    shepherd_sheep: str | None = None
    yaml: str | None = None
    zstandard: str | None = None

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
