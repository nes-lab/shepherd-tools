import pytest
from pytest import approx

from shepherd_core import CalibrationEmulator
from shepherd_core.data_models import VirtualHarvester
from shepherd_core.data_models import VirtualSource
from shepherd_core.data_models.content.virtual_harvester import HarvesterPRUConfig
from shepherd_core.vsource import VirtualHarvesterModel
from shepherd_core.vsource import VirtualSourceModel

# virtual_converter_model gets tested below with vsrc_model

hrv_list = [
    "ivcurve",
    "iv1000",
    "isc_voc",
    "cv20",
    "mppt_voc",
    "mppt_bq",
    "mppt_bq_solar",
    "mppt_po",
    "mppt_opt",
]


@pytest.mark.parametrize("hrv_name", hrv_list)
def test_vsource_hrv_min(hrv_name: str) -> None:
    hrv_config = VirtualHarvester(name=hrv_name)
    hrv_pru = HarvesterPRUConfig.from_vhrv(hrv_config)
    _ = VirtualHarvesterModel(hrv_pru)
    # TODO: do more


src_list = [
    "neutral",
    "direct",
    "diode+capacitor",
    "diode+resistor+capacitor",
    "BQ25504",
    "BQ25504s",
    "BQ25570",
    "BQ25570s",
]


def src_model(name: str) -> VirtualSourceModel:
    src_config = VirtualSource(name=name)
    cal_emu = CalibrationEmulator()
    return VirtualSourceModel(src_config, cal_emu, log_intermediate=True)


def c_leak_fWs(src: VirtualSourceModel, iterations: int) -> float:
    return iterations * src.cnv.V_mid_uV * src.cfg_src.I_intermediate_leak_nA


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
    assert src.W_out_fWs == approx(c_leak_fWs(src, iterations), rel=1e-4, abs=1e-6)


def test_vsource_vsrc_static2() -> None:
    iterations = 2_000
    src = src_model("BQ25504")
    for _ in range(iterations):
        src.iterate_sampling(V_inp_uV=0, I_inp_nA=3_000_000)
    assert src.W_inp_fWs == 0.0
    assert src.W_out_fWs == approx(c_leak_fWs(src, iterations), rel=1e-4, abs=1e-6)


@pytest.mark.parametrize("src_name", src_list[2:])
def test_vsource_charge(src_name: str) -> None:
    iterations = 4_000
    src = src_model(src_name)
    for v_mV in range(iterations):
        src.iterate_sampling(V_inp_uV=v_mV * 1000, I_inp_nA=1_000_000)
    v_out = src.iterate_sampling(V_inp_uV=1_000_000, I_inp_nA=1_000_000)
    assert src.W_inp_fWs > 0.0
    assert src.W_out_fWs == approx(c_leak_fWs(src, iterations), rel=0.12, abs=1e-3)
    assert v_out > 0.0


@pytest.mark.parametrize("src_name", src_list[4:])
def test_vsource_drain(src_name: str) -> None:
    iterations = 4_000
    src = src_model(src_name)
    for c_uA in range(iterations):
        src.iterate_sampling(I_out_nA=c_uA * 1000)
    v_out = src.iterate_sampling()
    assert src.W_inp_fWs == 0.0
    assert src.W_out_fWs > c_leak_fWs(src, iterations)
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

    for _ in range(iterations):
        src.iterate_sampling(V_inp_uV=5 * 10**6, I_inp_nA=4 * 10**6)
    v_out = src.iterate_sampling()
    assert v_out > 0

    assert src.W_out_fWs > 3 * c_leak_fWs(src, iterations)
    assert src.W_inp_fWs > src.W_out_fWs
