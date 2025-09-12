"""Script for generating YAML-fixture for virtual storage."""

import sys
from pathlib import Path

import yaml
from virtual_storage_config import VirtualStorageConfig

from shepherd_core import local_now
from shepherd_core.data_models import Wrapper
from shepherd_core.logger import log

dsc_ideal = "Model of an ideal Capacitor (true to spec, no losses)"
dsc_tantal = "Tantal-Capacitor similar to ideal Model, but with R_leak & R_series"
dsc_mlcc = "MLCC-Capacitor with R_leak & R_series and planned DC-Bias-Effect"
dsc_super = "SuperCapacitor with typically 1000 hours / 500 k cycles (not modeled)"

# Ideal Capacitor, E6 row 10 to 1000 uF
# typical voltage-ratings: 2.5, 4.0, 6.3, 10, 16, 20 V
E6: list[int] = [10, 15, 22, 33, 47, 68, 100, 150, 220, 330, 470, 680, 1000]
fixture_ideal: list[VirtualStorageConfig] = [
    VirtualStorageConfig.capacitor(C_uF=_v, V_rated=10.0, description=dsc_ideal) for _v in E6
]

# Tantal Capacitors, E6 row
# ⤷ verified with AVX TAJB107M006RNJ
#       - Tantal, 100 uF, 6V3, 20%, 1411 package -> 100 uF measured
#       - R_series taken from Datasheet
#       - R_leak = 1 MOhm in datasheet (6.3V/6.3uA), but ~2 MOhm in experiment
# see https://github.com/orgua/bq_characteristics/tree/main/eval_kit_behavior_var1#capacitor
fixture_tantal: list[VirtualStorageConfig] = [
    VirtualStorageConfig.capacitor(
        C_uF=10,
        V_rated=6.3,
        R_leak_Ohm=196e6 / 10,
        R_series_Ohm=3.0,
        name="AVX TAJB106x006",  # Note: small x is * in datasheet
        description=dsc_tantal,
    ),
    VirtualStorageConfig.capacitor(
        C_uF=15,
        V_rated=6.3,
        R_leak_Ohm=196e6 / 15,
        R_series_Ohm=2.0,
        name="AVX TAJB156x006",
        description=dsc_tantal,
    ),
    VirtualStorageConfig.capacitor(
        C_uF=22,
        V_rated=6.3,
        R_leak_Ohm=196e6 / 22,
        R_series_Ohm=2.5,
        name="AVX TAJB226x006",
        description=dsc_tantal,
    ),
    VirtualStorageConfig.capacitor(
        C_uF=33,
        V_rated=6.3,
        R_leak_Ohm=196e6 / 33,
        R_series_Ohm=2.2,
        name="AVX TAJB336x006",
        description=dsc_tantal,
    ),
    VirtualStorageConfig.capacitor(
        C_uF=47,
        V_rated=6.3,
        R_leak_Ohm=196e6 / 47,
        R_series_Ohm=2,
        name="AVX TAJB476x006",
        description=dsc_tantal,
    ),
    VirtualStorageConfig.capacitor(
        C_uF=68,
        V_rated=6.3,
        R_leak_Ohm=196e6 / 68,
        R_series_Ohm=0.9,
        name="AVX TAJB686x006",
        description=dsc_tantal,
    ),
    VirtualStorageConfig.capacitor(
        C_uF=100,
        V_rated=6.3,
        R_leak_Ohm=196e6 / 100,
        R_series_Ohm=1.7,
        name="AVX TAJB107x006",
        description=dsc_tantal,
    ),
    VirtualStorageConfig.capacitor(
        C_uF=150,
        V_rated=6.3,
        R_leak_Ohm=196e6 / 150,
        R_series_Ohm=1.3,
        name="AVX TAJC157x006",
        description=dsc_tantal,
    ),
    VirtualStorageConfig.capacitor(
        C_uF=220,
        V_rated=6.3,
        R_leak_Ohm=196e6 / 220,
        R_series_Ohm=1.2,
        name="AVX TAJC227x006",
        description=dsc_tantal,
    ),
    VirtualStorageConfig.capacitor(
        C_uF=330,
        V_rated=6.3,
        R_leak_Ohm=196e6 / 330,
        R_series_Ohm=0.5,
        name="AVX TAJC337x006",
        description=dsc_tantal,
    ),
    VirtualStorageConfig.capacitor(
        C_uF=470,
        V_rated=6.3,
        R_leak_Ohm=196e6 / 470,
        R_series_Ohm=0.4,
        name="AVX TAJD477x006",
        description=dsc_tantal,
    ),
]

# MLCC
# ⤷ verified with Taiyo Yuden JMK316ABJ107ML-T
#       - MLCC, 100uF, 6V3, 20%, X5R, 1206 package -> 74 uF measured
#       - Insulation Resistance (min) 100 MΩ·μF (datasheet), 97.8 MΩ measured
# https://github.com/orgua/bq_characteristics/tree/main/eval_kit_behavior_var1/data_capacitor
# BQ25570EVM uses Murata GRM43SR60J107ME20L
#       - MLCC, 100uF, 6V3, 20%, X5R, 1812 package -> 79 uF measured
#       - murata-DB does not know this part, but direct substitute is GRM31CR60J107MEA8
# https://pim.murata.com/en-global/pim/details/?partNum=GRM31CR60J107MEA8%23
# TODO: add DC-Bias
fixture_mlcc: list[VirtualStorageConfig] = [
    VirtualStorageConfig.capacitor(
        C_uF=10, V_rated=6.3, R_leak_Ohm=97.8e6 / 10, description=dsc_mlcc
    ),
    VirtualStorageConfig.capacitor(
        C_uF=33, V_rated=6.3, R_leak_Ohm=97.8e6 / 33, description=dsc_mlcc
    ),
    VirtualStorageConfig.capacitor(
        C_uF=47, V_rated=6.3, R_leak_Ohm=97.8e6 / 47, description=dsc_mlcc
    ),
    VirtualStorageConfig.capacitor(
        C_uF=100, V_rated=6.3, R_leak_Ohm=97.8e6 / 100, description=dsc_mlcc
    ),
]

# SuperCap
fixture_super: list[VirtualStorageConfig] = [
    VirtualStorageConfig.capacitor(
        C_uF=25e6,
        V_rated=3.0,
        R_leak_Ohm=3 / 55e-6,
        R_series_Ohm=17e-3,
        name="Maxwell BCAP0025 P300 X11",
        description=dsc_super,
    ),
    VirtualStorageConfig.capacitor(
        C_uF=12e6,
        V_rated=6.0,
        R_leak_Ohm=6 / 80e-6,
        R_series_Ohm=90e-3,
        name="Abracon ADCM-S06R0SA126RB",
        description=dsc_super,
    ),
    VirtualStorageConfig.capacitor(
        C_uF=7.5e6,
        V_rated=5.5,
        R_leak_Ohm=6 / 78e-6,
        R_series_Ohm=90e-3,
        name="AVX SCMT32F755SRBA0 ",
        description=dsc_super,
    ),
]

fixture_lipo: list[VirtualStorageConfig] = [
    # LiPo-Coin-cells 5.4mm, https://www.lipobatteries.net/3-8v-rechargeable-mini-button-lipo-coin-cell-battery/
    VirtualStorageConfig.lipo(
        capacity_mAh=80, name="LPM1254", description="LiPo-Coin-Cell 80mAh, 1 cell, w=12mm, d=5.4mm"
    ),
    VirtualStorageConfig.lipo(
        capacity_mAh=65, name="LPM1154", description="LiPo-Coin-Cell 65mAh, 1 cell, w=11mm, d=5.4mm"
    ),
    VirtualStorageConfig.lipo(
        capacity_mAh=50, name="LPM1054", description="LiPo-Coin-Cell 50mAh, 1 cell, w=10mm, d=5.4mm"
    ),
    VirtualStorageConfig.lipo(
        capacity_mAh=40, name="LPM0954", description="LiPo-Coin-Cell 40mAh, 1 cell, w=9mm, d=5.4mm"
    ),
    VirtualStorageConfig.lipo(
        capacity_mAh=35, name="LPM0854", description="LiPo-Coin-Cell 35mAh, 1 cell, w=8mm, d=5.4mm"
    ),
    # LiPo-Coin-cells 4.0mm, https://www.lipobatteries.net/3-8v-rechargeable-mini-button-lipo-coin-cell-battery/
    VirtualStorageConfig.lipo(
        capacity_mAh=55, name="LPM1240", description="LiPo-Coin-Cell 55mAh, 1 cell, w=12mm, d=4.0mm"
    ),
    VirtualStorageConfig.lipo(
        capacity_mAh=45, name="LPM1140", description="LiPo-Coin-Cell 45mAh, 1 cell, w=11mm, d=4.0mm"
    ),
    VirtualStorageConfig.lipo(
        capacity_mAh=35, name="LPM1040", description="LiPo-Coin-Cell 35mAh, 1 cell, w=10mm, d=4.0mm"
    ),
    VirtualStorageConfig.lipo(
        capacity_mAh=30, name="LPM0940", description="LiPo-Coin-Cell 30mAh, 1 cell, w=9mm, d=4.0mm"
    ),
    VirtualStorageConfig.lipo(
        capacity_mAh=18, name="LPM0840", description="LiPo-Coin-Cell 18mAh, 1 cell, w=8mm, d=4.0mm"
    ),
    # small LiPos, https://www.lipobatteries.net/lipo-batteries-within-100mah/
    VirtualStorageConfig.lipo(
        capacity_mAh=12, name="LP151020", description="LiPo-Pouch 12mAh, 1 cell, 20x10x1.5mm"
    ),
    VirtualStorageConfig.lipo(
        capacity_mAh=15, name="LP251212", description="LiPo-Pouch 15mAh, 1 cell, 12x12x2.5mm"
    ),
    VirtualStorageConfig.lipo(
        capacity_mAh=22, name="LP500522", description="LiPo-Pouch 20mAh, 1 cell, 22x05x5.0mm"
    ),
    VirtualStorageConfig.lipo(
        capacity_mAh=22, name="LP271015", description="LiPo-Pouch 22mAh, 1 cell, 15x10x2.7mm"
    ),
    # Example from the paper
    VirtualStorageConfig.lipo(capacity_mAh=860, name="PL-383562"),
]

fixture_lead: list[VirtualStorageConfig] = [
    # Example from the paper
    VirtualStorageConfig.lead_acid(capacity_mAh=1200, name="LEOCH_LP12-1.2AH"),
]


if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()
    path_db = path_here  # .parent / "shepherd_core/shepherd_core/data_models/content"

    if not path_db.exists() or not path_db.is_dir():
        log.error("Path to db must exist and be a directory!")
        sys.exit(1)

    fixtures: dict[str, list[VirtualStorageConfig]] = {
        "ideal": fixture_ideal,
        "tantal": fixture_tantal,
        "mlcc": fixture_mlcc,
        "super": fixture_super,
        "lipo": fixture_lipo,
        "lead": fixture_lead,
    }

    for name, fixture in fixtures.items():
        file_path = path_db / f"virtual_storage_fixture_{name}.yaml"
        if file_path.exists():
            log.warning("File %s already exists! -> will skip", file_path.name)
        models_wrap = []
        for model in fixture:
            model_dict = (
                model.model_dump()
            )  # exclude_unset=True, exclude_defaults=True, include={"id",})
            model_wrap = Wrapper(
                datatype=type(model).__name__,
                created=local_now(),
                comment=f"created by script '{Path(__file__).name}'",
                parameters=model_dict,
            )
            models_wrap.append(model_wrap.model_dump(exclude_unset=True, exclude_defaults=True))

        models_yaml = yaml.safe_dump(models_wrap, default_flow_style=False, sort_keys=False)
        with file_path.open("w") as f:
            f.write(models_yaml)
