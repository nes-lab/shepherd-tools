from shepherd_core.data_models.content import EnergyDType
from shepherd_core.data_models.content import EnergyEnvironment
from shepherd_core.data_models.content import Firmware
from shepherd_core.data_models.content import FirmwareDType
from shepherd_core.data_models.content import VirtualHarvester
from shepherd_core.data_models.content import VirtualSource
from shepherd_core.data_models.testbed import MCU


def test_content_model_min_ee1():
    EnergyEnvironment(
        id=9999,
        name="some",
        data_path="./file",
        data_type="isc_voc",
        duration=1,
        energy_Ws=0.1,
        owner="jane",
        group="wayne",
    )


def test_content_model_min_ee2():
    EnergyEnvironment(
        id="98765",
        name="some",
        data_path="./file",
        data_type=EnergyDType.ivcurve,
        duration=999,
        energy_Ws=3.1,
        owner="jane",
        group="wayne",
    )


def test_content_model_min_fw():
    Firmware(
        id=9999,
        name="dome",
        mcu=MCU(name="nRF52"),
        data="xyz",
        data_type=FirmwareDType.base64_hex,
        owner="Obelix",
        group="Gaul",
    )


def test_content_model_min_hrv():
    VirtualHarvester(
        id=9999,
        name="whatever",
        owner="jane",
        group="wayne",
    )


def test_content_model_min_src():
    VirtualSource(
        id=9999,
        name="new_src",
        owner="jane",
        group="wayne",
    )
