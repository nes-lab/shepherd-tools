"""Container for a common configuration.

This can be adapted by the user by importing 'config' and changing its variables.
"""

from collections.abc import Set as AbstractSet
from pathlib import PurePosixPath

from pydantic import BaseModel
from pydantic import HttpUrl


class CoreConfig(BaseModel):
    """Container for a common configuration."""

    __slots__ = ()

    testbed_name: str = "shepherd_tud_nes"
    """ ⤷ name of the testbed to validate against - if enabled - see switch below.
          this name will be updated if a client connects to another testbed.
    """
    validate_infrastructure: bool = False
    """ ⤷ switch to turn on / off deep validation of data models also considering the current
    layout & infrastructure of the testbed.
    """

    # CONSTANTS below
    TESTBED_SERVER: HttpUrl = "https://shepherd.cfaed.tu-dresden.de:8000/"
    """ ⤷ Server that hosts the desired shepherd-API."""
    TESTBED_TIMEOUT: int = 3
    """ ⤷ requests will fail after this many seconds."""

    SAMPLERATE_SPS: int = 100_000
    """ ⤷ Rate of IV-Recording of the testbed."""

    UID_NAME: str = "SHEPHERD_NODE_ID"
    """ ⤷ Variable name to patch in ELF-file"""
    UID_SIZE: int = 2
    """ ⤷ Variable size in Byte"""

    PATHS_ALLOWED: AbstractSet[PurePosixPath] = {
        PurePosixPath("/var/shepherd/"),
        PurePosixPath("/tmp/"),  # noqa: S108
    }


core_config = CoreConfig()
