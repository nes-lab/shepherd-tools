from shepherd_core.data_models.content.energy_environment import EnergyEnvironment
from shepherd_core.data_models.content.energy_environment import fixtures as fix_ee
from shepherd_core.data_models.content.firmware import Firmware
from shepherd_core.data_models.content.firmware import fixtures as fix_firmware
from shepherd_core.data_models.content.virtual_harvester import VirtualHarvester
from shepherd_core.data_models.content.virtual_harvester import fixtures as fix_hrv
from shepherd_core.data_models.content.virtual_source import VirtualSource
from shepherd_core.data_models.content.virtual_source import fixtures as fix_src


def test_testbed_fixture_energy_environment():
    for fix in fix_ee:
        name = fix["name"]
        EnergyEnvironment(name=name)
        uid = fix["uid"]
        EnergyEnvironment(uid=uid)


def test_testbed_fixture_firmware():
    for fix in fix_firmware:
        name = fix["name"]
        uid = fix["uid"]
        if uid in [1001, 1002]:
            continue
        Firmware(name=name)
        Firmware(uid=uid)


def test_experiment_fixture_vsrc():
    for fix in fix_src:
        name = fix["name"]
        VirtualSource(name=name)
        uid = fix["uid"]
        VirtualSource(uid=uid)


def test_experiment_fixture_vhrv():
    for fix in fix_hrv:
        name = fix["name"]
        if name == "neutral":
            continue
        VirtualHarvester(name=name)
        uid = fix["uid"]
        VirtualHarvester(uid=uid)
