"""Module for content-type data-models.

These models import externally from: /base, /testbed.
"""

from shepherd_core.data_models.base.content import ContentModel
from shepherd_core.data_models.base.wrapper import Wrapper

from .energy_environment import EnergyEnvironment
from .energy_environment import EnergyProfile
from .enum_datatypes import Compression
from .enum_datatypes import EnergyDType
from .enum_datatypes import FirmwareDType
from .firmware import Firmware
from .virtual_harvester_config import VirtualHarvesterConfig
from .virtual_source_config import VirtualSourceConfig
from .virtual_storage_config import VirtualStorageConfig

__all__ = [
    "Compression",
    "EnergyDType",
    "EnergyEnvironment",
    "EnergyProfile",
    "Firmware",
    "FirmwareDType",
    "VirtualHarvesterConfig",
    "VirtualSourceConfig",
    "VirtualStorageConfig",
]

content_supported = {name.lower(): name for name in __all__}


def instantiate_content(model_type: str, model_data: dict) -> ContentModel | None:
    """Make the individual content usable as the data-model.

    This is a copy of content.instantiate_component()
    """
    import sys  # noqa: PLC0415

    model_type = model_type.lower()
    if model_type == Wrapper.__name__.lower():
        return instantiate_content(model_data["datatype"], model_data["parameters"])
    if model_type not in content_supported:
        return None
    class_ = getattr(sys.modules[__name__], content_supported[model_type])
    return class_(**model_data)  # TODO: should we raise?
