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

from shepherd_core.logger import log
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.data_models.testbed.gpio import GPIO

# defaults (pre-init complex types)
zero_duration = timedelta(seconds=0)


class PowerTracing(ShpModel, title="Config for Power-Tracing"):
    """Configuration for recording the Power-Consumption of the Target Nodes.

    TODO: postprocessing not implemented ATM
    """

    intermediate_voltage: bool = False
    """
    ⤷ for EMU: record storage capacitor instead of output (good for V_out = const)
               this also includes current!
    """
    # time
    delay: timedelta = zero_duration
    """start recording after experiment started"""
    duration: Optional[timedelta] = None  # till EOF
    """duration of recording after delay starts the process.

    default is None, recording till EOF"""

    # post-processing
    calculate_power: bool = False
    """ ⤷ reduce file-size by calculating power -> not implemented ATM"""
    samplerate: Annotated[int, Field(ge=10, le=100_000)] = 100_000
    """ ⤷ reduce file-size by down-sampling -> not implemented ATM"""
    discard_current: bool = False
    """ ⤷ reduce file-size by omitting current -> not implemented ATM"""
    discard_voltage: bool = False
    """ ⤷ reduce file-size by omitting voltage -> not implemented ATM"""

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

    This feature allows to remove unwanted pins from recording,
    i.e. for chatty pins with separate UART Logging enabled.
    Numbering is based on the Target-Port and its 16x GPIO and two PwrGood-Signals.
    See doc for nRF_FRAM_Target_v1.3+ to see mapping of target port.

    Example for skipping UART (pin 0 & 1):
    .gpio = range(2,18)

    Note:
    - Cape 2.4 (2023) and lower only has 9x GPIO + 1x PwrGood
    - Cape 2.5 (2025) has first 12 GPIO & both PwrGood
    - this will be mapped accordingly by the observer
    """

    # time
    delay: timedelta = zero_duration
    duration: Optional[timedelta] = None  # till EOF

    # post-processing,
    uart_decode: bool = False
    """Automatic decoding from gpio-trace not implemented ATM."""
    uart_pin: GPIO = GPIO(name="GPIO8")
    uart_baudrate: Annotated[int, Field(ge=2_400, le=1_152_000)] = 115_200

    @model_validator(mode="after")
    def post_validation(self) -> Self:
        if self.delay and self.delay.total_seconds() < 0:
            raise ValueError("Delay can't be negative.")
        if self.duration and self.duration.total_seconds() < 0:
            raise ValueError("Duration can't be negative.")
        if self.uart_decode:
            log.error(
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
    """ ⤷ from start_time

    - resolution 10 us (guaranteed, but finer steps are possible)
    """
    gpio: GPIO
    level: GpioLevel
    period: Annotated[float, Field(ge=10e-6)] = 1
    """ ⤷ time base of periodicity in s"""
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

    @model_validator(mode="after")
    def post_validation(self) -> Self:
        msg = "not implemented ATM"
        raise ValueError(msg)

    def get_gpios(self) -> set:
        return {_ev.gpio for _ev in self.events}


class SystemLogging(ShpModel, title="Config for System-Logging"):
    """Configuration for recording Debug-Output of the Observers System-Services."""

    kernel: bool = True
    time_sync: bool = True
    sheep: bool = True
    sys_util: bool = True

    # deprecated, TODO: remove lines below before public release
    dmesg: Annotated[bool, deprecated("for sheep v0.9.0+, use 'kernel' instead")] = True
    ptp: Annotated[bool, deprecated("for sheep v0.9.0+, use 'time_sync' instead")] = True
    shepherd: Annotated[bool, deprecated("for sheep v0.9.0+, use 'sheep' instead")] = True


# TODO: some more interaction would be good
#     - execute limited python-scripts
#     - send uart-frames
