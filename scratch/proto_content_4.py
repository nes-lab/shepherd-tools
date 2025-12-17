"""Fourth prototype for an improved EEnv-Dataclass.

Mix of Prototype 1 & 2 with additional refinements.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from shepherd_core.data_models.content import EnergyDType
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import EnergyProfile
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.experiment import TargetConfig

from shepherd_core import log

# TODO:
#   - add unittests
#   - check eenv Paths in experiment
#   - add & change metadata of converters
#   - add metadata to generators

"""
RenamedInProfile
    data_local: bool = True -> data_2_copy
Moved2Profile
    data_path: Path
    data_type: EnergyDType
    duration: PositiveFloat
    energy_Ws: PositiveFloat
    valid: bool = False
NewInProfile:
    repetitions_OK
Removed:
    light_source: str | None = None
    weather_conditions: str | None = None
    indoor: bool | None = None
    location: str | None = None
"""

if __name__ == "__main__":
    with TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        path1 = Path(tmp) / "shp1.h5"
        path2 = Path(tmp) / "shp3.h5"
        path1.touch()
        path2.touch()
        profile1 = EnergyProfile(
            data_path=path1,
            data_type=EnergyDType.ivtrace,
            energy_Ws=1.0,
            duration=23,
        )
        profile2 = EnergyProfile(
            data_path=path2,
            data_type=EnergyDType.ivtrace,
            energy_Ws=3.0,
            duration=20,
        )
        eenv1 = EnergyEnvironment(
            name="t1", profiles=[profile1, profile2], metadata={"location": "tunesia"}
        )
        print(f"Duration: {eenv1.duration}")
        print(f"Repetitions: {eenv1.repetitions_ok}")

        eenv2a = eenv1[1:]
        eenv2b = eenv1[:1]
        eenv2 = eenv2a + eenv2b
        log.info(f"EEnv2a\t{eenv2a.model_dump(exclude_unset=True, exclude_defaults=True)}")
        log.info(f"EEnv2b\t{eenv2b.model_dump(exclude_unset=True, exclude_defaults=True)}")
        log.info(f"EEnv2\t{eenv2.model_dump(exclude_unset=True, exclude_defaults=True)}")
        eenv2.to_file(Path(__file__).parent / "eenv2.yaml", minimal=True)

        eenv3 = eenv1 + eenv1
        log.info(f"EEnv3\t{eenv1.model_dump(exclude_unset=True, exclude_defaults=True)}")
        eenv3.to_file(Path(__file__).parent / "eenv3.yaml", minimal=True)

        profileR = EnergyProfile(
            data_path=Path(tmp) / "shp5.h5",
            data_type=EnergyDType.ivtrace,
            energy_Ws=3.0,
            duration=20,
            repetitions_ok=True,
        )
        eenvR = EnergyEnvironment(name="t1", profiles=[profileR])
        eenvR.to_file(Path(__file__).parent / "eenvR.yaml", minimal=True)

        log.info("Config 1 - 2:2")
        TargetConfig(
            target_IDs=range(2), energy_env=eenv1, firmware1=Firmware(name="nrf52_deep_sleep")
        )
        log.info("Config 2 - 1:2")
        TargetConfig(
            target_IDs=range(1), energy_env=eenv2, firmware1=Firmware(name="nrf52_deep_sleep")
        )
        log.info("Config 3 - 3:1R")
        tc3 = TargetConfig(
            target_IDs=range(3), energy_env=eenvR, firmware1=Firmware(name="nrf52_deep_sleep")
        )
        log.info("Config 4 - 4:4")
        TargetConfig(
            target_IDs=range(4), energy_env=eenv3, firmware1=Firmware(name="nrf52_deep_sleep")
        )
        log.info("Config 5 - 4:2 -> raises")
        TargetConfig(
            target_IDs=range(4), energy_env=eenv1, firmware1=Firmware(name="nrf52_deep_sleep")
        )
