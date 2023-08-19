import platform
import subprocess  # noqa: S404
import time
from contextlib import suppress
from typing import Optional

from .. import logger

try:
    import psutil

    psutil_support = True
except ImportError:
    psutil_support = False

from pydantic import ConfigDict
from pydantic.types import PositiveInt

from ..data_models import ShpModel


class SystemInventory(ShpModel):
    uptime: PositiveInt
    # ⤷ seconds

    system: str
    release: str
    version: str

    machine: str
    processor: str

    ptp: Optional[str] = None

    hostname: str

    interfaces: dict = {}
    # ⤷ tuple with
    #   ip IPvAnyAddress
    #   mac MACStr

    model_config = ConfigDict(str_min_length=0)

    @classmethod
    def collect(cls):
        if psutil_support:
            ifs1 = psutil.net_if_addrs().items()
            ifs2 = {
                name: (_if[1].address, _if[0].address)
                for name, _if in ifs1
                if len(_if) > 1
            }
            uptime = time.time() - psutil.boot_time()
        else:
            ifs2 = {}
            uptime = 0
            logger.warning(
                "Inventory-Parameters will be missing. "
                "Please install functionality with "
                "'pip install shepherd_core[inventory] -U' first"
            )

        model_dict = {
            "uptime": round(uptime),
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
