import pytest
from pydantic import ValidationError

from shepherd_core.data_models.testbed import GPIO
from shepherd_core.data_models.testbed import MCU
from shepherd_core.data_models.testbed import Cape
from shepherd_core.data_models.testbed import Direction
from shepherd_core.data_models.testbed import Observer
from shepherd_core.data_models.testbed import ProgrammerProtocol
from shepherd_core.data_models.testbed import Target
from shepherd_core.data_models.testbed import Testbed as TasteBad

# ⤷ TasteBad avoids pytest-warning


def test_testbed_model_cape_min() -> None:
    cape = Cape(
        id=9999,
        name="cappi",
        version="1.0.0",
        description="lorem",
    )
    print(cape)


def test_testbed_model_gpio_min() -> None:
    gpio = GPIO(
        id=9999,
        name="gippi",
        reg_pru="ABCD",
        pin_pru="EFGH",
    )
    print(gpio)


def test_testbed_model_gpio_fault() -> None:
    with pytest.raises(ValidationError):
        GPIO(
            id=9999,
            name="gippi",
        )


def test_testbed_model_gpio_var() -> None:
    GPIO(
        id=9999,
        name="gippi",
        direction=Direction.Bidirectional,
        reg_pru="ABCD",
        pin_pru="EFGH",
    )


def test_testbed_model_mcu_min() -> None:
    mcu = MCU(
        id=9922,
        name="controller2",
        description="lorem",
        platform="arm32",
        core="STM32F7",
        prog_protocol=ProgrammerProtocol.SWD,
        fw_name_default="nananana",
    )
    print(mcu)


def test_testbed_model_observer_min() -> None:
    obs = Observer(
        id=9933,
        name="sheep120",
        description="not existing",
        ip="127.0.0.1",
        mac="FF:FF:FF:FF:FF:FF",
        room="IIE72",
        eth_port="375b2",
        cape=Cape(name="cape53"),
    )
    print(obs)


def test_testbed_model_observer_fault_cape_a() -> None:
    with pytest.raises(ValidationError):
        Observer(
            id=9933,
            name="sheep120",
            description="not existing",
            ip="127.0.0.1",
            mac="FF:FF:FF:FF:FF:FF",
            room="IIE72",
            eth_port="375b2",
            target_a=Target(id=3),
        )


def test_testbed_model_observer_fault_cape_b() -> None:
    with pytest.raises(ValidationError):
        Observer(
            id=9933,
            name="sheep120",
            description="not existing",
            ip="127.0.0.1",
            mac="FF:FF:FF:FF:FF:FF",
            room="IIE72",
            eth_port="375b2",
            target_b=Target(id=3),
        )


def test_testbed_model_observer_fault_target() -> None:
    obs = Observer(
        id=9933,
        name="sheep120",
        description="not existing",
        ip="127.0.0.1",
        mac="FF:FF:FF:FF:FF:FF",
        room="IIE72",
        eth_port="375b2",
        cape=Cape(name="cape53"),
        target_a=Target(id=3),
        target_b=Target(id=2),
    )
    obs.get_target(2)
    obs.get_target(3)
    obs.get_target_port(2)
    obs.get_target_port(3)
    with pytest.raises(KeyError):
        obs.get_target_port(123456)
    with pytest.raises(KeyError):
        obs.get_target(123456)


def test_testbed_model_target_min1() -> None:
    tgt = Target(
        id=9944,
        name="TerraTarget",
        version="v1.00",
        description="lorem",
        mcu1=MCU(name="MSP430FR"),
    )
    print(tgt)


def test_testbed_model_target_min2() -> None:
    Target(
        id=9944,
        name="TerraTarget",
        version="v1.00",
        description="lorem",
        mcu1="MSP430FR",
        mcu2="MSP430FR",
    )


def test_testbed_model_tb_min() -> None:
    tb = TasteBad(
        name="shepherd",
        id="9955",
        description="lorem",
        observers=[Observer(name="sheep02")],
        data_on_server="/mnt/driveA",
        data_on_observer="/mnt/driveB",
    )
    print(tb)


def test_testbed_model_tb_fault_observer() -> None:
    with pytest.raises(ValidationError):
        TasteBad(
            name="shepherd",
            id="9955",
            description="lorem",
            observers=[Observer(name="sheep02"), Observer(name="sheep02")],
            data_on_server="/mnt/driveA",
            data_on_observer="/mnt/driveB",
        )


def test_testbed_model_tb_fault_shared() -> None:
    with pytest.raises(ValidationError):
        TasteBad(
            name="shepherd",
            id="9955",
            description="lorem",
            observers=[Observer(name="sheep02")],
            data_on_server="/mnt/driveA",
            data_on_observer="/mnt/driveB",
            shared_storage=False,
        )
