from pathlib import Path

from shepherd_core.data_models.content import VirtualSourceConfig
from shepherd_core.data_models.experiment import Experiment
from shepherd_core.data_models.task import EmulationTask
from shepherd_core.data_models.task import HarvestTask
from shepherd_core.data_models.testbed.testbed import Testbed as TasteBad

from .conftest import load_yaml

# ⤷ TasteBad avoids pytest-warning


def test_example_emu() -> None:
    data_dict = load_yaml("example_config_emulator.yaml")
    assert data_dict["mode"] == "emulator"
    emu = EmulationTask(**data_dict["parameters"])
    print(emu)


def test_example_hrv() -> None:
    data_dict = load_yaml("example_config_harvester.yaml")
    assert data_dict["mode"] == "harvester"
    emu = HarvestTask(**data_dict["parameters"])
    print(emu)


def test_example_exp_recommended() -> None:
    # new way
    path = Path(__file__).with_name("example_config_experiment.yaml")
    Experiment.from_file(path)


def test_example_exp() -> None:
    # non-optimal / old way
    data_dict = load_yaml("example_config_experiment_alternative.yaml")
    Experiment(**data_dict)


def test_example_tb() -> None:
    data_dict = load_yaml("example_config_testbed.yaml")
    print(data_dict)
    TasteBad(**data_dict)


def test_example_vsrc() -> None:
    data_dict = load_yaml("example_config_virtsource.yaml")
    VirtualSourceConfig(**data_dict["VirtualSource"])
