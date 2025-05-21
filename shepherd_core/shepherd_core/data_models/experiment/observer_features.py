"""Configs for observer features like gpio- & power-tracing."""

from datetime import timedelta
from enum import Enum
from typing import Annotated
from typing import Optional

import numpy as np
from annotated_types import Interval
from pydantic import Field
from pydantic import PositiveFloat
from pydantic import model_validator
from typing_extensions import Self
from typing_extensions import deprecated

from shepherd_core import logger
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.data_models.testbed.gpio import GPIO


class PowerTracing(ShpModel, title="Config for Power-Tracing"):
    """Configuration for recording the Power-Consumption of the Target Nodes.

    TODO: postprocessing not implemented ATM
    """

    intermediate_voltage: bool = False
    # ⤷ for EMU: record storage capacitor instead of output (good for V_out = const)
    #            this also includes current!

    # time
    delay: timedelta = timedelta(seconds=0)
    duration: Optional[timedelta] = None  # till EOF

    # post-processing
    calculate_power: bool = False
    samplerate: Annotated[int, Field(ge=10, le=100_000)] = 100_000  # down-sample
    discard_current: bool = False
    discard_voltage: bool = False
    # ⤷ reduce file-size by omitting current / voltage

    @model_validator(mode="after")
    def post_validation(self) -> Self:
        if self.delay and self.delay.total_seconds() < 0:
            raise ValueError("Delay can't be negative.")
        if self.duration and self.duration.total_seconds() < 0:
            raise ValueError("Duration can't be negative.")

        discard_all = self.discard_current and self.discard_voltage
        if not self.calculate_power and discard_all:
            raise ValueError("Error in config -> tracing enabled, but output gets discarded")
        if self.calculate_power:
            raise NotImplementedError(
                "Feature PowerTracing.calculate_power reserved for future use."
            )
        if self.samplerate != 100_000:
            raise NotImplementedError("Feature PowerTracing.samplerate reserved for future use.")
        if self.discard_current:
            raise NotImplementedError(
                "Feature PowerTracing.discard_current reserved for future use."
            )
        if self.discard_voltage:
            raise NotImplementedError(
                "Feature PowerTracing.discard_voltage reserved for future use."
            )
        return self


# NOTE: this was taken from pyserial (removes one dependency)
BAUDRATES = (
    50,
    75,
    110,
    134,
    150,
    200,
    300,
    600,
    1200,
    1800,
    2400,
    4800,
    9600,
    19200,
    38400,
    57600,
    115200,
    230400,
    460800,
    500000,
    576000,
    921600,
    1000000,
    1152000,
    1500000,
    2000000,
    2500000,
    3000000,
    3500000,
    4000000,
)

PARITY_NONE, PARITY_EVEN, PARITY_ODD, PARITY_MARK, PARITY_SPACE = "N", "E", "O", "M", "S"
PARITIES = (PARITY_NONE, PARITY_EVEN, PARITY_ODD, PARITY_MARK, PARITY_SPACE)

STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO = (1, 1.5, 2)
STOPBITS = (STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO)


class UartLogging(ShpModel, title="Config for UART Logging"):
    """Configuration for recording UART-Output of the Target Nodes.

    Note that the Communication has to be on a specific port that
    reaches the hardware-module of the SBC.
    """

    baudrate: Annotated[int, Field(ge=2_400, le=460_800)] = 115_200
    # ⤷ TODO: find maximum that the system can handle
    bytesize: Annotated[int, Field(ge=5, le=8)] = 8
    stopbits: Annotated[float, Field(ge=1, le=2)] = 1
    parity: str = PARITY_NONE

    @model_validator(mode="after")
    def post_validation(self) -> Self:
        if self.baudrate not in BAUDRATES:
            msg = f"Error in config -> baud-rate must be one of: {BAUDRATES}"
            raise ValueError(msg)
        if self.stopbits not in STOPBITS:
            msg = f"Error in config -> stop-bits must be one of: {STOPBITS}"
            raise ValueError(msg)
        if self.parity not in PARITIES:
            msg = f"Error in config -> parity must be one of: {PARITIES}"
            raise ValueError(msg)
        return self


GpioInt = Annotated[int, Interval(ge=0, le=17)]
GpioList = Annotated[list[GpioInt], Field(min_length=1, max_length=18)]
all_gpio = list(range(18))


class GpioTracing(ShpModel, title="Config for GPIO-Tracing"):
    """Configuration for recording the GPIO-Output of the Target Nodes.

    TODO: postprocessing not implemented ATM
    """

    gpios: GpioList = all_gpio
    """List of GPIO to record.

    Numbering is based on the Target-Port and its GPIO.
    To make the Port future-safer it offers 16x GPIO and 2x PwrGood.
    See doc for nRF_FRAM_Target_v1.3+ to see mapping of target port.

    Note:
    - Cape 2.4 (2023) and lower only has 9x GPIO + 1x PwrGood
    - Cape 2.5 (2025) has 12x GPIO & both PwrGood
    """

    # time
    delay: timedelta = timedelta(seconds=0)
    duration: Optional[timedelta] = None  # till EOF

    # post-processing,
    uart_decode: bool = False
    uart_pin: GPIO = GPIO(name="GPIO8")
    uart_baudrate: Annotated[int, Field(ge=2_400, le=1_152_000)] = 115_200

    @model_validator(mode="after")
    def post_validation(self) -> Self:
        if self.delay and self.delay.total_seconds() < 0:
            raise ValueError("Delay can't be negative.")
        if self.duration and self.duration.total_seconds() < 0:
            raise ValueError("Duration can't be negative.")
        if self.uart_decode:
            logger.error(
                "Feature GpioTracing.uart_decode reserved for future use. "
                "Use UartLogging or manually decode serial with the provided waveform decoder."
            )
        return self

    @property
    def gpio_mask(self) -> int:
        # valid for cape v2.5
        mask = 0
        for gpio in set(self.gpios):
            mask |= 2**gpio
        return mask


class GpioLevel(str, Enum):
    """Options for setting the gpio-level or state."""

    low = "L"
    high = "H"
    toggle = "X"  # TODO: not the smartest decision for writing a converter


class GpioEvent(ShpModel, title="Config for a GPIO-Event"):
    """Configuration for a single GPIO-Event (Actuation)."""

    delay: PositiveFloat
    # ⤷ from start_time
    # ⤷ resolution 10 us (guaranteed, but finer steps are possible)
    gpio: GPIO
    level: GpioLevel
    period: Annotated[float, Field(ge=10e-6)] = 1
    # ⤷ time base of periodicity in s
    count: Annotated[int, Field(ge=1, le=4096)] = 1

    @model_validator(mode="after")
    def post_validation(self) -> Self:
        if not self.gpio.user_controllable():
            msg = f"GPIO '{self.gpio.name}' in actuation-event not controllable by user"
            raise ValueError(msg)
        return self

    def get_events(self) -> np.ndarray:
        stop = self.delay + self.count * self.period
        return np.arange(self.delay, stop, self.period)


class GpioActuation(ShpModel, title="Config for GPIO-Actuation"):
    """Configuration for a GPIO-Actuation-Sequence."""

    # TODO: not implemented ATM - decide if pru control sys-gpio or
    # TODO: not implemented ATM - reverses pru-gpio (preferred if possible)

    events: Annotated[list[GpioEvent], Field(min_length=1, max_length=1024)]

    def get_gpios(self) -> set:
        return {_ev.gpio for _ev in self.events}


class SystemLogging(ShpModel, title="Config for System-Logging"):
    """Configuration for recording Debug-Output of the Observers System-Services."""

    kernel: bool = True
    time_sync: bool = True
    sheep: bool = True
    sys_util: bool = True

    # TODO: remove lines below in 2026
    dmesg: Annotated[bool, deprecated("for sheep v0.9.0+, use 'kernel' instead")] = True
    ptp: Annotated[bool, deprecated("for sheep v0.9.0+, use 'time_sync' instead")] = True
    shepherd: Annotated[bool, deprecated("for sheep v0.9.0+, use 'sheep' instead")] = True


# TODO: some more interaction would be good
#     - execute limited python-scripts
#     - send uart-frames
