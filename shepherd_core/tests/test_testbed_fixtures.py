from shepherd_core.data_models.testbed.cape import Cape
from shepherd_core.data_models.testbed.cape import fixtures as fix_cape
from shepherd_core.data_models.testbed.gpio import GPIO
from shepherd_core.data_models.testbed.gpio import fixtures as fix_gpio
from shepherd_core.data_models.testbed.mcu import MCU
from shepherd_core.data_models.testbed.mcu import fixtures as fix_mcu
from shepherd_core.data_models.testbed.observer import Observer
from shepherd_core.data_models.testbed.observer import fixtures as fix_observer
from shepherd_core.data_models.testbed.target import Target
from shepherd_core.data_models.testbed.target import fixtures as fix_target


def test_testbed_fixture_cape():
    for fix in fix_cape:
        Cape(name=fix["name"])
        Cape(uid=fix["uid"])


def test_testbed_fixture_gpio():
    for fix in fix_gpio:
        GPIO(name=fix["name"])
        GPIO(uid=fix["uid"])


def test_testbed_fixture_mcu():
    for fix in fix_mcu:
        MCU(name=fix["name"])
        MCU(uid=fix["uid"])


def test_testbed_fixture_observer():
    for fix in fix_observer:
        Observer(name=fix["name"])
        Observer(uid=fix["uid"])


def test_testbed_fixture_target():
    for fix in fix_target:
        Target(name=fix["name"])
        Target(uid=fix["uid"])
