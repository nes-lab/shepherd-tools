import os
from pathlib import Path

import pytest

from shepherd_data import ivonne
from shepherd_data import mppt


@pytest.fixture
def file_ivonne() -> Path:
    path = Path(__file__).resolve().parent.parent.parent.parent / "shepherd_data/examples"
    os.chdir(path)
    return path / "./jogging_10m.iv"


@pytest.fixture
def file_isc_voc(file_ivonne: Path) -> Path:
    path = file_ivonne.parent / "jogging_10m_isc_voc.h5"
    if not path.exists():
        with ivonne.Reader(file_ivonne) as db:
            db.upsample_2_isc_voc(path, duration_s=1)
    return path


@pytest.fixture
def file_ivcurve(file_ivonne: Path) -> Path:
    path = file_ivonne.parent / "jogging_10m_ivcurve.h5"
    if not path.exists():
        with ivonne.Reader(file_ivonne) as db:
            db.convert_2_ivcurves(path, duration_s=1)
    return path


@pytest.fixture
def file_ivsample(file_ivonne: Path) -> Path:
    path = file_ivonne.parent / "jogging_10m_ivsample.h5"
    if not path.exists():
        with ivonne.Reader(file_ivonne) as db:
            tr_opt = mppt.OptimalTracker()
            db.convert_2_ivsamples(path, tracker=tr_opt, duration_s=1)
    return path


@pytest.fixture
def _file_cleanup(file_isc_voc: Path, file_ivcurve: Path, file_ivsample: Path) -> None:
    file_isc_voc.unlink(missing_ok=True)
    file_ivcurve.unlink(missing_ok=True)
    file_ivsample.unlink(missing_ok=True)
