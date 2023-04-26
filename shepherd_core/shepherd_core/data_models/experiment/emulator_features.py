from typing import List
from typing import Optional

from pydantic import conint

from .. import ShpModel
from ..testbed import GPIO


class PowerLogging(ShpModel):
    # initial recording
    log_voltage: bool = True
    log_current: bool = True
    # compression -> to Emu, TODO
    log_intermediate_voltage: bool = False  # TODO: duplicate in PowerSampling()

    # post-processing, TODO: not supported ATM
    calculate_power: bool = False
    samplerate: conint(ge=100, le=100_000) = 100_000
    discard_current: bool = False
    discard_voltage: bool = False


class GpioLogging(ShpModel):
    # initial recording
    log_gpio: bool = False  # TODO: activate
    mask: conint(ge=0, le=2**10) = 2**10  # all
    gpios: Optional[List[GPIO]]  # TODO: list of GPIO to build mask

    # post-processing, TODO: not supported ATM
    decode_uart: bool = False
    baudrate_uart: conint(ge=2_400, le=921_600) = 115_200
    # TODO: more uart-config -> dedicated interface?


class SystemLogging(ShpModel):
    log_dmesg: bool = False  # TODO: activate
    log_ptp: bool = False  # TODO: activate
