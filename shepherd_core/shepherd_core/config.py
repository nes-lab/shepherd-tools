"""Container for a common configuration.

This can be adapted by the user by importing 'config' and changing its variables.
"""

from collections.abc import Set as AbstractSet
from pathlib import PurePosixPath

from pydantic import BaseModel
from pydantic import HttpUrl


class ConfigDefault(BaseModel):
    """Container for a common configuration."""

    __slots__ = ()

    TESTBED: str = "shepherd_tud_nes"
    """name of the testbed to validate against - if enabled - see switch below"""
    VALIDATE_INFRA: bool = True
    """switch to turn on / off deep validation of data models also considering the current
    layout & infrastructure of the testbed.
    """

    SAMPLERATE_SPS: int = 100_000
    """Rate of IV-Recording of the testbed."""

    UID_NAME: str = "SHEPHERD_NODE_ID"
    """Variable name to patch in ELF-file"""
    UID_SIZE: int = 2
    """Variable size in Byte"""

    TESTBED_SERVER: HttpUrl = HttpUrl("https://shepherd.cfaed.tu-dresden.de:8000/")
    """Server that holds up to date testbed fixtures"""

    PATHS_ALLOWED: AbstractSet[PurePosixPath] = {
        PurePosixPath("/var/shepherd/"),
        PurePosixPath("/tmp/"),  # noqa: S108
    }


config = ConfigDefault()
