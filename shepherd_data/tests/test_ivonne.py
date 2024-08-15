from pathlib import Path

import pytest

from shepherd_data import Reader
from shepherd_data import ivonne
from shepherd_data import mppt


@pytest.fixture
def example_path() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent / "examples"


def test_convert_ivonne(tmp_path: Path, example_path: Path) -> None:
    input_file = "jogging_10m"
    inp_path = example_path / (input_file + ".iv")
    isc_path = tmp_path / (input_file + "_isc.h5")
    ivc_path = tmp_path / (input_file + "_ivc.h5")
    voc_path = tmp_path / (input_file + "_voc.h5")
    opt_path = tmp_path / (input_file + "_opt.h5")

    with ivonne.Reader(inp_path) as ifr:
        ifr.upsample_2_isc_voc(isc_path, duration_s=20)
        ifr.convert_2_ivcurves(ivc_path, duration_s=20)

        tr_voc = mppt.OpenCircuitTracker(ratio=0.76)
        tr_opt = mppt.OptimalTracker()

        ifr.convert_2_ivsamples(voc_path, tracker=tr_voc, duration_s=20)
        ifr.convert_2_ivsamples(opt_path, tracker=tr_opt, duration_s=20)

    energies = {}
    for file_path in [isc_path, ivc_path, voc_path, opt_path]:
        with Reader(file_path) as sfr:
            assert sfr.runtime_s == 20
            energies[file_path.stem[-3:]] = sfr.energy()

    assert energies["isc"] > energies["opt"]
    assert energies["opt"] > energies["voc"]
    assert energies["voc"] > energies["ivc"]
