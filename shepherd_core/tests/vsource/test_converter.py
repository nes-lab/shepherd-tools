from pathlib import Path

import pytest
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models import VirtualSourceConfig
from shepherd_core.vsource import VirtualSourceModel

from shepherd_core import CalibrationEmulator
from shepherd_core import Reader

# virtual_converter_model gets tested below with vsrc_model

src_list = [
    "direct",
    "diode+capacitor",
    "diode+resistor+capacitor",
    "BQ25504",
    "BQ25504s",
    "BQ25570",
    "BQ25570s",
]


def src_model(
    name: str,
    dtype_in: EnergyDType = EnergyDType.ivsample,
    window_size: int | None = None,
    voltage_step_V: float | None = None,
) -> VirtualSourceModel:
    src_config = VirtualSourceConfig(name=name)
    cal_emu = CalibrationEmulator()
    return VirtualSourceModel(
        src_config,
        cal_emu,
        log_intermediate=False,
        dtype_in=dtype_in,
        window_size=window_size,
        voltage_step_V=voltage_step_V,
    )


@pytest.mark.parametrize("src_name", src_list)
def test_vsource_vsrc_min(src_name: str) -> None:
    src = src_model(src_name)
    src.iterate_sampling()


def test_vsource_vsrc_static1() -> None:
    iterations = 2_000
    src = src_model("BQ25504")
    for _ in range(iterations):
        src.iterate_sampling(V_inp_uV=3_000_000, I_inp_nA=0)
    assert src.W_inp_fWs == 0.0
    assert src.W_out_fWs == 0.0  # -> leakage now locally in storage
    # pytest.approx(c_leak_fWs(src, iterations), rel=1e-4, abs=1e-6))


def test_vsource_vsrc_static2() -> None:
    iterations = 2_000
    src = src_model("BQ25504")
    for _ in range(iterations):
        src.iterate_sampling(V_inp_uV=0, I_inp_nA=3_000_000)
    assert src.W_inp_fWs == 0.0
    assert src.W_out_fWs == 0.0  # -> leakage now locally in storage


@pytest.mark.parametrize("src_name", src_list[2:])
def test_vsource_charge(src_name: str) -> None:
    iterations = 8_000
    src = src_model(src_name)
    for v_mV in range(iterations):
        src.iterate_sampling(V_inp_uV=10**6 + v_mV * 1000, I_inp_nA=1_500_000)
    v_out = src.iterate_sampling(V_inp_uV=1_000_000, I_inp_nA=1_000_000)
    assert src.W_inp_fWs > 0.0
    assert src.W_out_fWs == 0.0  # -> leakage now locally in storage
    assert v_out > 0.0


@pytest.mark.parametrize("src_name", src_list[4:])
def test_vsource_drain(src_name: str) -> None:
    iterations = 4_000
    src = src_model(src_name)
    assert src.W_inp_fWs == 0.0
    # pre-charge and then drain
    for v_mV in range(iterations):
        src.iterate_sampling(V_inp_uV=v_mV * 1000, I_inp_nA=2_000_000)
    src.W_inp_fWs = 0.0
    for c_uA in range(iterations):
        src.iterate_sampling(I_out_nA=c_uA * 1000)
    v_out = src.iterate_sampling()
    assert src.W_inp_fWs == 0.0
    assert src.W_out_fWs > 0.0  # -> leakage now locally in storage
    assert v_out >= 0.0


def test_vsource_vsrc_over_voltage() -> None:
    iterations = 100
    src = src_model("BQ25504")
    for _ in range(iterations):
        src.iterate_sampling(V_inp_uV=10 * 10**6, I_inp_nA=3_000_000)
    assert src.cnv.V_input_uV <= 5 * 10**6
    assert src.W_inp_fWs > 0.0


def test_vsource_vsrc_over_current() -> None:
    iterations = 100
    src = src_model("BQ25504")
    for _ in range(iterations):
        src.iterate_sampling(V_inp_uV=5 * 10**6, I_inp_nA=100 * 10**6)
    assert src.W_inp_fWs > 0.0


def test_vsource_vsrc_cycle() -> None:
    iterations = 2000
    src = src_model("BQ25504s")

    for _ in range(iterations):
        src.iterate_sampling(V_inp_uV=5 * 10**6, I_inp_nA=4 * 10**6)
    v_out = src.iterate_sampling()
    assert v_out > 0

    for _ in range(iterations):
        src.iterate_sampling(I_out_nA=40 * 10**6)
    v_out = src.iterate_sampling()
    assert v_out == 0
    # TODO: not accurate anymore as the output does not get disconnected for this BQ

    for _ in range(iterations):
        src.iterate_sampling(V_inp_uV=5 * 10**6, I_inp_nA=20 * 10**6)
    v_out = src.iterate_sampling()
    assert v_out > 0

    assert src.W_out_fWs > 0.0  # -> leakage now locally in storage
    assert src.W_inp_fWs > src.W_out_fWs


def test_vsource_vsrc_create_files(
    file_ivcurve: Path, file_ivsample: Path, file_isc_voc: Path
) -> None:
    pass


@pytest.mark.parametrize("src_name", src_list)
def test_vsource_vsrc_sim_curve(src_name: str, file_ivcurve: Path) -> None:
    with Reader(file_ivcurve) as file:
        src = src_model(
            "BQ25504s",
            dtype_in=file.get_datatype(),
            window_size=file.get_window_samples(),
            voltage_step_V=file.get_voltage_step(),
        )
        for _, v_, i_ in file.read():
            length = max(v_.size, i_.size)
            for n_ in range(length):
                src.iterate_sampling(V_inp_uV=v_[n_] * 10**6, I_inp_nA=i_[n_] * 10**9)


@pytest.mark.parametrize("src_name", src_list)
def test_vsource_vsrc_sim_sample(src_name: str, file_ivsample: Path) -> None:
    with Reader(file_ivsample) as file:
        src = src_model(
            "BQ25504s",
            dtype_in=file.get_datatype(),
            window_size=file.get_window_samples(),
            voltage_step_V=file.get_voltage_step(),
        )
        for _, v_, i_ in file.read():
            length = max(v_.size, i_.size)
            for n_ in range(length):
                src.iterate_sampling(V_inp_uV=v_[n_] * 10**6, I_inp_nA=i_[n_] * 10**9)
