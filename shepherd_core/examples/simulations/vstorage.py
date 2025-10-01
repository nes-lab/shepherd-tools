"""A set of experiments to validate and qualify the virtual storage algorithms.

Some general Notes:

- ShpCap is also displayed when emulating Lipo and lead-acid, but it can't and won't behave similar
- during charging the model KiBaM-Plus will deviate from normal KiBaM and KiBaM-Simple,
  as it supports the rate capacity effect and transients (during charging)

"""

import multiprocessing
from datetime import timedelta
from pathlib import Path

from pydantic import PositiveFloat
from pydantic import validate_call
from shepherd_core.data_models.content.virtual_storage_config import VirtualStorageConfig
from shepherd_core.data_models.content.virtual_storage_config import soc_t
from shepherd_core.vsource.virtual_storage_model import ModelStorage
from shepherd_core.vsource.virtual_storage_model import VirtualStorageModel
from shepherd_core.vsource.virtual_storage_models_kibam import ModelKiBaM
from shepherd_core.vsource.virtual_storage_models_kibam import ModelKiBaMPlus
from shepherd_core.vsource.virtual_storage_models_kibam import ModelKiBaMSimple
from shepherd_core.vsource.virtual_storage_models_kibam import ModelShpCap
from shepherd_core.vsource.virtual_storage_simulator import StorageSimulator

from shepherd_core import log

path_here = Path(__file__).parent


@validate_call
def get_models(
    SoC_init: soc_t, config: VirtualStorageConfig, dt_s: PositiveFloat
) -> list[ModelStorage]:
    """Models to include in experiments."""
    return [
        ModelKiBaM(SoC_init=SoC_init, cfg=config, dt_s=dt_s),
        ModelKiBaMPlus(SoC_init=SoC_init, cfg=config, dt_s=dt_s),
        ModelKiBaMSimple(SoC_init=SoC_init, cfg=config, dt_s=dt_s, optimize_clamp=True),
        ModelKiBaMSimple(SoC_init=SoC_init, cfg=config, dt_s=dt_s, interpolate=True),
        VirtualStorageModel(SoC_init=SoC_init, cfg=config, dt_s=dt_s),
        ModelShpCap(SoC_init=SoC_init, cfg=config, dt_s=dt_s),
    ][1:5]


class CurrentPulsed:
    """A simple constant current source that is pulsed until a target SoC is reached."""

    @validate_call
    def __init__(
        self,
        I_pulse: float,
        period_pulse: PositiveFloat,
        duration_pulse: PositiveFloat,
        SoC_target: soc_t,
    ) -> None:
        self.I_pulse = I_pulse
        self.period_pulse = period_pulse
        self.duration_pulse = duration_pulse
        self.SoC_target = SoC_target

    def step(self, t_s: float, SoC: float, _v: float) -> float:
        if (self.I_pulse < 0 and SoC <= self.SoC_target) or (
            self.I_pulse > 0 and SoC >= self.SoC_target
        ):
            return 0
        return self.I_pulse if t_s % self.period_pulse < self.duration_pulse else 0


class ResistiveChargePulsed:
    """A pulsed charger that is 'current limited' by a resistor."""

    @validate_call
    def __init__(
        self,
        V_target: PositiveFloat,
        R_Ohm: PositiveFloat,
        period_pulse: PositiveFloat,
        duration_pulse: PositiveFloat,
    ) -> None:
        self.R_Ohm = R_Ohm
        self.V_target = V_target
        self.period_pulse = period_pulse
        self.duration_pulse = duration_pulse

    def step(self, t_s: float, _s: float, V: float) -> float:
        I_A = (self.V_target - V) / self.R_Ohm
        return I_A if t_s % self.period_pulse < self.duration_pulse else 0


def experiment_current_ramp_pos(config: VirtualStorageConfig) -> None:
    """Charge virtual storage with a positive current ramp (increasing power)."""
    dt_s = 0.1
    SoC_start = 0.5
    duration_s = 200
    sim = StorageSimulator(
        models=get_models(SoC_start, config, dt_s),
        dt_s=dt_s,
    )

    def current_trace(t_s: float, _s: float, _v: float) -> float:
        return 0.1 + 0.15 * t_s / duration_s  # pru-model can handle +- 268 mA

    sim.run(fn=current_trace, duration_s=250)
    sim.plot(path_here, f"XP {config.name}, current charge ramp (positive)")


def experiment_current_ramp_neg(config: VirtualStorageConfig) -> None:
    """Discharge virtual storage with a negative current ramp (increasing power)."""
    dt_s = 0.1
    SoC_start = 0.5
    duration_s = 200
    sim = StorageSimulator(
        models=get_models(SoC_start, config, dt_s),
        dt_s=dt_s,
    )

    def current_trace(t_s: float, _s: float, _v: float) -> float:
        return -(0.1 + 0.14 * t_s / duration_s)  # pru-model can handle +- 268 mA

    sim.run(fn=current_trace, duration_s=duration_s)
    sim.plot(path_here, f"XP {config.name}, current discharge ramp (negative)")


def experiment_pulsed_discharge(config: VirtualStorageConfig) -> None:
    """Discharge virtual storage with a pulsed constant current."""
    dt_s = 0.2
    SoC_start = 1.0
    SoC_target = 0.0
    i_pulse = CurrentPulsed(
        I_pulse=-0.1, period_pulse=200, duration_pulse=100, SoC_target=SoC_target
    )  # pru-model can handle +- 268 mA
    sim = StorageSimulator(
        models=get_models(SoC_start, config, dt_s),
        dt_s=dt_s,
    )
    sim.run(fn=i_pulse.step, duration_s=1_000)
    sim.plot(path_here, f"XP {config.name}, pulsed discharge .1A, 1000 s (figure_9a)")


def experiment_pulsed_charge(config: VirtualStorageConfig) -> None:
    """Charge virtual storage with a pulsed constant current."""
    dt_s = 0.2
    SoC_start = 0.0
    SoC_target = 1.0
    i_pulse = CurrentPulsed(
        I_pulse=0.1, period_pulse=200, duration_pulse=100, SoC_target=SoC_target
    )  # pru-model can handle +- 268 mA
    sim = StorageSimulator(
        models=get_models(SoC_start, config, dt_s),
        dt_s=dt_s,
    )
    sim.run(fn=i_pulse.step, duration_s=1_000)
    sim.plot(path_here, f"XP {config.name}, pulsed charge .1A, 1000 s (figure_9b)")


def experiment_pulsed_resistive_charge(config: VirtualStorageConfig) -> None:
    """Charge virtual storage with a resistive constant voltage."""
    dt_s = 0.5
    SoC_start = 0.0
    i_pulse = ResistiveChargePulsed(R_Ohm=20, V_target=4.2, period_pulse=200, duration_pulse=100)
    sim = StorageSimulator(
        models=get_models(SoC_start, config, dt_s),
        dt_s=dt_s,
    )
    sim.run(fn=i_pulse.step, duration_s=3_000)
    sim.plot(path_here, f"XP {config.name}, pulsed resistive charge 20 Ohm to 4.2 V, 3000 s")


def experiment_resistive_load(config: VirtualStorageConfig) -> None:
    """Charge virtual storage with a resistive constant voltage."""
    dt_s = 0.5
    SoC_start = 1.0

    def i_charge(_t_s: float, _s: float, V: float) -> float:
        return -V / 20

    sim = StorageSimulator(
        models=get_models(SoC_start, config, dt_s),
        dt_s=dt_s,
    )
    sim.run(fn=i_charge, duration_s=1_000)
    sim.plot(path_here, f"XP {config.name}, resistive load 20 Ohm from 4.2 V, 1000 s")


def experiment_self_discharge() -> None:
    """Observe self-discharge behavior of virtual storage models."""
    dt_s = 0.2
    SoC_start = 1.0
    SoC_target = 0.9
    duration = timedelta(minutes=25)
    store = VirtualStorageConfig.capacitor(C_uF=100, V_rated=6.3)
    R_leak = store.calc_R_leak_capacitor(duration=duration, SoC_final=SoC_target, SoC_0=SoC_start)
    log.info("R_leak = %.2f Ohm", R_leak)
    config = VirtualStorageConfig.capacitor(C_uF=100, V_rated=6.3, R_leak_Ohm=R_leak)
    sim = StorageSimulator(
        models=get_models(SoC_start, config, dt_s),
        dt_s=dt_s,
    )

    def step(_t: float, _s: float, _v: float) -> float:
        return 0

    sim.run(fn=step, duration_s=duration.total_seconds())
    sim.plot(
        path_here,
        f"XP {config.name}, self-discharge, "
        f"SoC {SoC_start} to {SoC_target} in {duration.total_seconds()} s",
    )


if __name__ == "__main__":
    with multiprocessing.Pool() as pool:
        pool.apply_async(experiment_self_discharge)

        configs = [
            VirtualStorageConfig.capacitor(C_uF=10e6, V_rated=4.2),  # match charge with batteries
            VirtualStorageConfig.lipo(q_mAh=10),
            VirtualStorageConfig.lead_acid(q_mAh=10),
        ]

        for cfg in configs:
            pool.apply_async(experiment_pulsed_charge, args=(cfg,))
            pool.apply_async(experiment_pulsed_discharge, args=(cfg,))
            pool.apply_async(experiment_current_ramp_pos, args=(cfg,))
            pool.apply_async(experiment_current_ramp_neg, args=(cfg,))

        for cfg in configs[0:2]:
            pool.apply_async(experiment_pulsed_resistive_charge, args=(cfg,))
            pool.apply_async(experiment_resistive_load, args=(cfg,))

        pool.close()
        pool.join()
