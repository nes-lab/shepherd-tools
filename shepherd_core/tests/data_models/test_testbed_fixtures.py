from shepherd_core.data_models.content.firmware import Firmware
from shepherd_core.data_models.testbed.cape import Cape
from shepherd_core.data_models.testbed.gpio import GPIO
from shepherd_core.data_models.testbed.mcu import MCU
from shepherd_core.data_models.testbed.observer import Observer
from shepherd_core.data_models.testbed.target import Target
from shepherd_core.data_models.testbed.testbed import Testbed
from shepherd_core.testbed_client.fixtures import Fixtures


def test_testbed_fixture_cape() -> None:
    for fix in Fixtures()["Cape"]:
        Cape(name=fix["name"])
        # Cape(id=fix["id"])


def test_testbed_fixture_gpio() -> None:
    for fix in Fixtures()["GPIO"]:
        GPIO(name=fix["name"])
        GPIO(id=fix["id"])


def test_testbed_fixture_mcu() -> None:
    for fix in Fixtures()["MCU"]:
        mcu = MCU(name=fix["name"])
        # mcu = MCU(id=fix["id"])
        Firmware(name=mcu.fw_name_default)


def test_testbed_fixture_observer() -> None:
    for fix in Fixtures()["Observer"]:
        print(f"selecting {fix.get('name')} - {fix.get('id')}")
        Observer(name=fix["name"])
        # Observer(id=fix["id"])


def test_testbed_fixture_target() -> None:
    for fix in Fixtures()["Target"]:
        Target(name=fix["name"])
        # Target(id=fix["id"])


def test_testbed_fixture_tb() -> None:
    for fix in Fixtures()["Testbed"]:
        Testbed(name=fix["name"])
        # Testbed(id=fix["id"])
        # IDs partly removed in non-content models
