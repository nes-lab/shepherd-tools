
import pytest
import numpy as np
from pathlib import Path

from click.testing import CliRunner

from shepherd_data import Reader, Writer
from shepherd_data.cli import cli


def random_data(length):
    return np.random.randint(0, high=2 ** 18, size=length, dtype="u4")


@pytest.fixture
def data_h5_path(tmp_path) -> Path:
    store_path = tmp_path / "harvest_example.h5"

    with Writer(store_path, compression=1) as file:

        file.set_hostname("artificial")

        duration_s = 10
        repetitions = 4
        timestamp_vector = np.arange(0.0, duration_s, file.sample_interval_ns / 1e9)

        # values in SI units
        voltages = np.linspace(3.60, 1.90, int(file.samplerate_sps * duration_s))
        currents = np.linspace(100e-6, 2000e-6, int(file.samplerate_sps * duration_s))

        for idx in range(repetitions):
            timestamps = idx * duration_s + timestamp_vector
            file.append_iv_data_si(timestamps, voltages, currents)

    return store_path


def test_cli_invoke_help():
    res = CliRunner().invoke(
        cli, ["-h"]
    )
    assert res.exit_code == 0


def test_cli_validate_file(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", str(data_h5_path)]
    )
    assert res.exit_code == 0


def test_cli_validate_dir(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", str(data_h5_path.absolute().parent)]
    )
    assert res.exit_code == 0


def test_cli_extract_file_full(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", str(data_h5_path), "--ds_factor", "100", "--separator", ","]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".downsampled_x100.h5").exists()
    assert data_h5_path.with_suffix(".data.h5").exists()


def test_cli_extract_file_short(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", str(data_h5_path), "-f", "200", "-s", ";"]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".downsampled_x200.h5").exists()
    assert data_h5_path.with_suffix(".data.h5").exists()


def test_cli_extract_file_min(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", str(data_h5_path)]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".downsampled_x1000.h5").exists()
    assert data_h5_path.with_suffix(".data.h5").exists()
