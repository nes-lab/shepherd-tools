"""Module for testbed-related data-models.

These models import externally from: /base
"""

from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.data_models.base.wrapper import Wrapper

from .cape import Cape
from .cape import TargetPort
from .gpio import GPIO
from .gpio import Direction
from .mcu import MCU
from .mcu import ProgrammerProtocol
from .observer import MACStr
from .observer import Observer
from .target import IdInt16
from .target import Target
from .testbed import Testbed

__all__ = [
    "GPIO",
    "MCU",
    "Cape",
    "Direction",
    "IdInt16",
    "MACStr",
    "Observer",
    "ProgrammerProtocol",
    "Target",
    "TargetPort",
    "Testbed",
]

components_supported = {name.lower(): name for name in __all__}


def instantiate_component(model_type: str, model_data: dict) -> ShpModel | None:
    """Make the individual content usable as the data-model.

    This is a copy of content.instantiate_content()
    """
    import sys  # noqa: PLC0415

    model_type = model_type.lower()
    if model_type == Wrapper.__name__.lower():
        return instantiate_component(model_data["datatype"], model_data["parameters"])
    if model_type not in components_supported:
        return None
    class_ = getattr(sys.modules[__name__], components_supported[model_type])
    return class_(**model_data)  # TODO: should we raise?
