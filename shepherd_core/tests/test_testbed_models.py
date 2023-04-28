from shepherd_core.data_models.testbed import GPIO
from shepherd_core.data_models.testbed import MCU
from shepherd_core.data_models.testbed import Cape
from shepherd_core.data_models.testbed import Direction
from shepherd_core.data_models.testbed import Observer
from shepherd_core.data_models.testbed import ProgrammerProtocol
from shepherd_core.data_models.testbed import Target


def test_testbed_model_min_cape():
    Cape(
        uid=9999,
        name="cappi",
        version="1.0.0",
        description="lorem",
    )


def test_testbed_model_min_gpio():
    GPIO(
        uid=9999,
        name="gippi",
        reg_pru="ABCD",
        pin_pru="EFGH",
    )


def test_testbed_model_var_gpio():
    GPIO(
        uid=9999,
        name="gippi",
        direction=Direction.Bidirectional,
        reg_pru="ABCD",
        pin_pru="EFGH",
    )


def test_testbed_model_min_mcu():
    MCU(
        uid=9922,
        name="controller2",
        description="lorem",
        platform="arm32",
        core="STM32F7",
        programmer=ProgrammerProtocol.SWD,
    )


def test_testbed_model_min_observer():
    Observer(
        uid=9933,
        name="sheep120",
        description="not existing",
        ip="127.0.0.1",
        mac="FF:FF:FF:FF:FF",
        room="IIE72",
        eth_port="375b2",
        cape=Cape(name="cape3"),
    )


def test_testbed_model_min_target():
    Target(
        uid=9944,
        name="TerraTarget",
        version="v1.00",
        description="lorem",
        mcu1=MCU(name="MSP430FR"),
    )
