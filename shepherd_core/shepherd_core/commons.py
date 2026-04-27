"""Container for commonly shared constants."""

from typing import Annotated

from typing_extensions import deprecated

from .config import core_config

SAMPLERATE_SPS_DEFAULT: Annotated[int, deprecated("use core.config.SAMPLERATE_SPS")] = (
    core_config.SAMPLERATE_SPS
)
