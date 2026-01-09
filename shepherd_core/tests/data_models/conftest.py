from pathlib import Path

import pytest
import yaml
from shepherd_core.data_models import EnergyProfile
from shepherd_core.data_models.content import EnergyDType


def load_yaml(file: str) -> dict:
    yaml_path = Path(__file__).resolve().with_name(file)
    with yaml_path.open() as data:
        return yaml.safe_load(data)


path_fwt = Path(__file__).parent.parent.resolve() / "fw_tools"
names_elf = ["build_msp.elf", "build_nrf.elf"]
files_elf = [path_fwt / name for name in names_elf]


@pytest.fixture
def energy_profiles(tmp_path: Path) -> list[EnergyProfile]:
    path1 = Path(tmp_path) / "shp1.h5"
    path2 = Path(tmp_path) / "shp3.h5"
    path1.touch()
    path2.touch()
    profile1 = EnergyProfile(
        data_path=path1,
        data_type=EnergyDType.ivtrace,
        valid=True,
        energy_Ws=1.0,
        duration=23,
    )
    profile2 = EnergyProfile(
        data_path=path2,
        data_type=EnergyDType.ivtrace,
        valid=True,
        energy_Ws=3.0,
        duration=20,
    )
    return [profile1, profile2]
