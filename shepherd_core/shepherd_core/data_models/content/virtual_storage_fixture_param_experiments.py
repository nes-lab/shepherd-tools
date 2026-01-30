"""Script to determine proper parameters for the fixtures.

This is done by comparing data from datasheets or online sources
with the resulting behavior of the model.
"""

from datetime import timedelta

from virtual_storage_config import VirtualStorageConfig

from shepherd_core import log
from shepherd_core.vsource.virtual_storage_models_kibam import ModelKiBaMPlus
from shepherd_core.vsource.virtual_storage_simulator import StorageSimulator


def experiment_self_discharge_lead_acid() -> None:
    """Determine leakage resistor and plot behavior.

    Datasheet of LEOCH LP12-1.2AH expects 3 to 20 % discharge/month
    -> chosen 5 % for the fixtures
    """
    dt_s = 10
    SoC_init = 1.0
    SoC_final = 0.95
    duration = timedelta(weeks=4)
    R_leak1 = VirtualStorageConfig.lead_acid(q_mAh=1).calc_R_leak_battery(
        duration, SoC_0=SoC_init, SoC_final=SoC_final
    )
    R_leak2 = (
        VirtualStorageConfig.lead_acid(q_mAh=10).calc_R_leak_battery(
            duration, SoC_0=SoC_init, SoC_final=SoC_final
        )
        * 10
    )
    log.info("R_leak_lead \t= %.0f Ohm [@1mAh]", R_leak1)
    if round(R_leak1) != round(R_leak2):
        raise ValueError("Values should match")
    cfg1 = VirtualStorageConfig.lead_acid(q_mAh=1200)
    sim = StorageSimulator(
        models=[ModelKiBaMPlus(SoC_init=SoC_init, cfg=cfg1, dt_s=dt_s)],
        dt_s=dt_s,
    )

    def step(_t: float, _s: float, _v: float) -> float:
        return 0

    sim.run(fn=step, duration_s=duration.total_seconds())
    sim.plot(
        f"Experiment {cfg1.name}, self-discharge, "
        f"SoC {SoC_init:.3f} to {SoC_final:.3f} in {duration.total_seconds()} s"
    )


def experiment_self_discharge_lipo() -> None:
    """Determine leakage resistor and plot behavior.

    According to wikipedia a typical Lipo looses 5 % in 4 weeks.
    """
    dt_s = 10
    SoC_init = 1.0
    SoC_final = 0.95
    duration = timedelta(weeks=4)
    R_leak1 = VirtualStorageConfig.lipo(q_mAh=1).calc_R_leak_battery(
        duration, SoC_0=SoC_init, SoC_final=SoC_final
    )
    R_leak2 = (
        VirtualStorageConfig.lipo(q_mAh=10).calc_R_leak_battery(
            duration, SoC_0=SoC_init, SoC_final=SoC_final
        )
        * 10
    )
    log.info("R_leak_lipo \t= %.0f Ohm [@1mAh]", R_leak1)
    if round(R_leak1) != round(R_leak2):
        raise ValueError("Values should match")
    cfg1 = VirtualStorageConfig.lipo(q_mAh=860)
    sim = StorageSimulator(
        models=[ModelKiBaMPlus(SoC_init=SoC_init, cfg=cfg1, dt_s=dt_s)],
        dt_s=dt_s,
    )

    def step(_t: float, _s: float, _v: float) -> float:
        return 0

    sim.run(fn=step, duration_s=duration.total_seconds())
    sim.plot(
        f"Experiment {cfg1.name}, self-discharge, "
        f"SoC {SoC_init:.3f} to {SoC_final:.3f} in {duration.total_seconds()} s"
    )


def experiment_self_discharge_tantal_avx() -> None:
    """Discharge Experiment: measured 5V to 3V decrease in 100 s.

    https://github.com/orgua/bq_characteristics/tree/main/eval_kit_behavior_var1#capacitor
    Note: first approach should be correct, but the second matches the plot
    """
    dt_s = 0.1
    cfg0 = VirtualStorageConfig.capacitor(C_uF=100, V_rated=6.3)
    duration = timedelta(seconds=100)
    R_leak = cfg0.calc_R_leak_battery(duration, SoC_final=3.0 / 5.0)
    log.info("R_leak_tantal \t= %.0f Ohm [@1uF]", R_leak * 100)
    cfg1 = VirtualStorageConfig.capacitor(
        C_uF=100, V_rated=6.3, R_leak_Ohm=R_leak, name="AVX TAJB107M006RNJ"
    )
    SoC_init = cfg1.approximate_SoC(V_OC=5.0)
    sim = StorageSimulator(
        models=[ModelKiBaMPlus(SoC_init=SoC_init, cfg=cfg1, dt_s=dt_s)],
        dt_s=dt_s,
    )

    def step(_t: float, _s: float, _v: float) -> float:
        return 0

    sim.run(fn=step, duration_s=duration.total_seconds())
    sim.plot(f"Experiment Tantal AVX, self-discharge {duration.total_seconds()} s")


def experiment_self_discharge_mlcc_tayo() -> None:
    """Discharge Experiment: measured 5V to 1.8V decrease in 100 s.

    Taiyo Yuden, JMK316ABJ107ML
    https://github.com/orgua/bq_characteristics/tree/main/eval_kit_behavior_var1#capacitor
    """
    dt_s = 0.1
    duration = timedelta(seconds=100)
    cfg0 = VirtualStorageConfig.capacitor(C_uF=74, V_rated=6.3)
    R_leak = cfg0.calc_R_leak_battery(duration, SoC_final=1.8 / 5.0)
    log.info("R_leak_mlcc \t= %.0f Ohm [@1uF]", R_leak * 74)
    R_leak = cfg0.calc_R_leak_capacitor(duration, SoC_final=1.8 / 5.0)
    log.info("R_leak_mlcc \t= %.0f Ohm [@1uF]", R_leak * 74)
    cfg1 = VirtualStorageConfig.capacitor(
        C_uF=74, V_rated=6.3, R_leak_Ohm=R_leak, name="Taiyo JMK316ABJ107ML"
    )
    SoC_init = cfg1.approximate_SoC(V_OC=5.0)
    sim = StorageSimulator(
        models=[ModelKiBaMPlus(SoC_init=SoC_init, cfg=cfg1, dt_s=dt_s)],
        dt_s=dt_s,
    )

    def step(_t: float, _s: float, _v: float) -> float:
        return 0

    sim.run(fn=step, duration_s=duration.total_seconds())
    sim.plot(f"Experiment MLCC Tayo, self-discharge {duration.total_seconds()} s")


if __name__ == "__main__":
    experiment_self_discharge_lead_acid()
    experiment_self_discharge_lipo()
    experiment_self_discharge_tantal_avx()
    experiment_self_discharge_mlcc_tayo()
