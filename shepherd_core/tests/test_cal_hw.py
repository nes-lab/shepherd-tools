from typing import Callable

import pytest

from shepherd_core.calibration_hw_def import adc_current_to_raw
from shepherd_core.calibration_hw_def import adc_raw_to_current
from shepherd_core.calibration_hw_def import adc_raw_to_voltage
from shepherd_core.calibration_hw_def import adc_voltage_to_raw
from shepherd_core.calibration_hw_def import dac_raw_to_voltage
from shepherd_core.calibration_hw_def import dac_voltage_to_raw


@pytest.mark.parametrize("fn", [adc_current_to_raw, adc_voltage_to_raw, dac_voltage_to_raw])
def test_convert_to_raw(fn: Callable) -> None:
    values = [-1, -1e-6, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1e-0]
    value_prev = -1
    for value in values:
        value_raw = fn(value)
        assert value_raw >= 0
        assert value_raw < 2**18
        assert value_raw >= value_prev
        value_prev = value_raw


@pytest.mark.parametrize("fn", [adc_raw_to_current, adc_raw_to_voltage, dac_raw_to_voltage])
def test_convert_to_si(fn: Callable) -> None:
    values = [-100, -1, 0, 1, 2**6, 2**12, 2**18, 2**24]
    value_prev = -1
    for value in values:
        value_si = fn(value)
        assert value_si >= 0
        assert value_si <= 6
        assert value_si >= value_prev
        value_prev = value_si
