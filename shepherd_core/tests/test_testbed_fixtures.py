from shepherd_core.data_models.testbed.cape import Cape
from shepherd_core.data_models.testbed.cape import fixtures as fix_cape
from shepherd_core.data_models.testbed.firmware import Firmware
from shepherd_core.data_models.testbed.firmware import fixtures as fix_firmware
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
        name = fix["name"]
        Cape(name=name)
        uid = fix["uid"]
        Cape(uid=uid)


def test_testbed_fixture_firmware():
    for fix in fix_firmware:
        name = fix["name"]
        Firmware(name=name)
        uid = fix["uid"]
        Firmware(uid=uid)


def test_testbed_fixture_gpio():
    for fix in fix_gpio:
        name = fix["name"]
        GPIO(name=name)
        uid = fix["uid"]
        GPIO(uid=uid)


def test_testbed_fixture_mcu():
    for fix in fix_mcu:
        name = fix["name"]
        MCU(name=name)
        uid = fix["uid"]
        MCU(uid=uid)


def test_testbed_fixture_observer():
    for fix in fix_observer:
        name = fix["name"]
        print(name)
        Observer(name=name)
        uid = fix["uid"]
        Observer(uid=uid)


def test_testbed_fixture_target():
    for fix in fix_target:
        name = fix["name"]
        Target(name=name)
        uid = fix["uid"]
        Target(uid=uid)
