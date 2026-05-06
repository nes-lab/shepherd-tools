"""Generalized energy harvester data models."""

import math
from typing import Annotated
from typing import final

from pydantic import Field
from typing_extensions import Self

from shepherd_core.config import core_config
from shepherd_core.data_models.base.shepherd import ShpModel

from .enum_datatypes import EnergyDType
from .virtual_harvester_config import VirtualHarvesterConfig

u32 = Annotated[int, Field(ge=0, lt=2**32)]


@final
class HarvesterPRUConfig(ShpModel):
    """Map settings-list to internal state-vars struct HarvesterConfig for PRU.

    NOTE:
      - yaml is based on si-units like nA, mV, ms, uF
      - c-code and py-copy is using nA, uV, ns, nF, fW, raw
      - ordering is intentional and in sync with shepherd/commons.h.
    """

    algorithm: u32
    hrv_mode: u32
    window_size: u32
    voltage_uV: u32
    voltage_min_uV: u32
    voltage_max_uV: u32
    voltage_step_uV: u32
    """ ⤷ for window-based algo like ivcurve"""
    current_limit_nA: u32
    """ ⤷ lower bound to detect zero current"""
    setpoint_n8: u32
    interval_n: u32
    """ ⤷ between measurements"""
    duration_n: u32
    """ ⤷ of measurement"""
    wait_cycles_n: u32
    """ ⤷ for DAC to settle"""
    cutout_cycles_n: u32
    """ ⤷ for large voltage-ramp transitions / resets to settle"""

    @classmethod
    def from_vhrv(
        cls,
        data: VirtualHarvesterConfig,
        dtype_in: EnergyDType | None = EnergyDType.ivsample,
        window_size: u32 | None = None,
        voltage_step_V: float | None = None,
        *,
        for_emu: bool = False,
    ) -> Self:
        if isinstance(dtype_in, str):
            dtype_in = EnergyDType[dtype_in]
        if for_emu and dtype_in not in {EnergyDType.ivsample, EnergyDType.ivcurve}:
            raise NotImplementedError

        if for_emu and dtype_in == EnergyDType.ivcurve and voltage_step_V is None:
            raise ValueError(
                "For correct emulation specify voltage_step used by harvester "
                "e.g. via file_src.get_voltage_step()"
            )

        if for_emu and dtype_in == EnergyDType.ivcurve and window_size is None:
            raise ValueError(
                "For correct emulation specify window_size used by harvester "
                "e.g. via file_src.get_window_size()"
            )

        interval_ms, duration_ms = data.calc_timings_ms(for_emu=for_emu)
        window_size = (
            window_size
            if window_size is not None
            else data.calc_window_size(dtype_in, for_emu=for_emu)
        )
        if voltage_step_V is not None:
            voltage_step_mV = 1e3 * voltage_step_V
        elif data.voltage_step_mV is not None:
            voltage_step_mV = data.voltage_step_mV
        else:
            raise ValueError(
                "For correct emulation specify voltage_step used by harvester "
                "e.g. via file_src.get_voltage_step()"
            )
        if (data.cutout_cycles > 0) and (window_size <= data.cutout_cycles):
            msg = (
                "Misconfiguration detected as vHrv.cutout_cycles is "
                f"larger than the actual window_size ({data.cutout_cycles} vs {window_size})."
            )
            raise ValueError(msg)

        return cls(
            algorithm=data.calc_algorithm_num(for_emu=for_emu),
            hrv_mode=data.calc_hrv_mode(for_emu=for_emu),
            window_size=window_size,
            voltage_uV=round(data.voltage_mV * 10**3),
            voltage_min_uV=round(data.voltage_min_mV * 10**3),
            voltage_max_uV=round(data.voltage_max_mV * 10**3),
            voltage_step_uV=math.ceil(voltage_step_mV * 10**3),
            current_limit_nA=round(data.current_limit_uA * 10**3),
            setpoint_n8=round(min(255, data.setpoint_n * 2**8)),
            interval_n=round(interval_ms * core_config.SAMPLERATE_SPS * 1e-3),
            duration_n=round(duration_ms * core_config.SAMPLERATE_SPS * 1e-3),
            wait_cycles_n=data.wait_cycles,
            cutout_cycles_n=data.cutout_cycles,
        )
