from enum import StrEnum
from typing import List
from typing import Optional

import yaml
from pydantic import PositiveFloat
from pydantic import confloat
from pydantic import conint

from .. import ShpModel
from ..model_shepherd import repr_str
from ..testbed import GPIO


class PowerTracing(ShpModel):
    # initial recording
    voltage: bool = True
    current: bool = True
    # compression -> to Emu, TODO
    intermediate_voltage: bool = False  # TODO: duplicate in PowerSampling()

    # time
    delay: conint(ge=0) = 0
    duration: Optional[conint(ge=0)] = None  # will be max

    # post-processing, TODO: not supported / implemented ATM
    calculate_power: bool = False
    samplerate: conint(ge=10, le=100_000) = 100_000  # downsample
    discard_current: bool = False
    discard_voltage: bool = False


class GpioTracing(ShpModel):
    # initial recording
    log_gpio: bool = False
    mask: conint(ge=0, lt=2**10) = 0b11_1111_1111  # all
    gpios: Optional[List[GPIO]]
    # ⤷ TODO: list of GPIO to build mask, one of both should be internal

    # time
    delay: conint(ge=0) = 1  # seconds
    duration: Optional[conint(ge=0)] = None  # will be max

    # post-processing, TODO: not supported ATM
    uart_decode: bool = False
    uart_pin: GPIO = GPIO(name="GPIO8")
    uart_baudrate: conint(ge=2_400, le=921_600) = 115_200
    # TODO: more uart-config -> dedicated interface?


class GpioLevel(StrEnum):
    low = "L"
    high = "H"
    toggle = "X"


yaml.add_representer(GpioLevel, repr_str)


class GpioEvent(ShpModel):  # TODO: not implemented
    delay: PositiveFloat  # resolution 10 us (guaranteed, but finer steps are possible)
    gpio: GPIO
    level: GpioLevel
    period: confloat(ge=10e-6)
    count: conint(ge=1, le=4096)


class GpioActuation(ShpModel):  # TODO: not implemented
    actions: list[GpioEvent] = []


class SystemLogging(ShpModel):
    log_dmesg: bool = False  # TODO: activate
    log_ptp: bool = False  # TODO: activate


# TODO: some more interaction would be good
#     - execute limited python-scripts
#     - send uart-frames
