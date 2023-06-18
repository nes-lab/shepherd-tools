from shepherd_core.data_models.content.firmware import Firmware
from shepherd_core.data_models.testbed.cape import Cape
from shepherd_core.data_models.testbed.gpio import GPIO
from shepherd_core.data_models.testbed.mcu import MCU
from shepherd_core.data_models.testbed.observer import Observer
from shepherd_core.data_models.testbed.target import Target
from shepherd_core.data_models.testbed.testbed import Testbed as TasteBad
from shepherd_core.testbed_client.fixtures import Fixtures

# ⤷ TasteBad avoids pytest-warning


def test_testbed_fixture_cape() -> None:
    for fix in Fixtures()["Cape"]:
        Cape(name=fix["name"])
        Cape(id=fix["id"])


def test_testbed_fixture_gpio() -> None:
    for fix in Fixtures()["GPIO"]:
        GPIO(name=fix["name"])
        GPIO(id=fix["id"])


def test_testbed_fixture_mcu() -> None:
    for fix in Fixtures()["MCU"]:
        MCU(name=fix["name"])
        mcu = MCU(id=fix["id"])
        Firmware(name=mcu.fw_name_default)


def test_testbed_fixture_observer() -> None:
    for fix in Fixtures()["Observer"]:
        Observer(name=fix["name"])
        Observer(id=fix["id"])


def test_testbed_fixture_target() -> None:
    for fix in Fixtures()["Target"]:
        Target(name=fix["name"])
        Target(id=fix["id"])


def test_testbed_fixture_tb() -> None:
    for fix in Fixtures()["Testbed"]:
        TasteBad(name=fix["name"])
        TasteBad(id=fix["id"])
