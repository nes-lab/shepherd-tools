import platform
import subprocess  # noqa: S404
import time
from contextlib import suppress
from typing import Optional

import psutil
from pydantic.types import PositiveInt

from ..data_models import ShpModel


class SystemInventory(ShpModel):
    uptime: PositiveInt
    # seconds

    system: str
    release: str
    version: str

    machine: str
    processor: str

    ptp: Optional[str] = None

    hostname: str

    interfaces: dict = {}
    # tuple with
    #   ip IPvAnyAddress
    #   mac MACStr

    class Config:
        min_anystr_length = 0

    @classmethod
    def collect(cls):
        ifs1 = psutil.net_if_addrs().items()
        ifs2 = {
            name: (_if[1].address, _if[0].address) for name, _if in ifs1 if len(_if) > 1
        }

        model_dict = {
            "uptime": time.time() - psutil.boot_time(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "interfaces": ifs2,
        }

        with suppress(FileNotFoundError):
            ret = subprocess.run(["/usr/sbin/ptp4l", "-v"])  # noqa: S603
            model_dict["ptp"] = ret.stdout
            # alternative: check_output - seems to be lighter

        return cls(**model_dict)
