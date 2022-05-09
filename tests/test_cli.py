
import pytest
import numpy as np
from pathlib import Path

from click.testing import CliRunner

from shepherd_data import Reader, Writer
from shepherd_data.cli import cli


def generate_h5_file(file_path: Path, file_name: str = "harvest_example.h5") -> Path:
    store_path = file_path / file_name

    with Writer(store_path, compression=1) as file:

        file.set_hostname("artificial")

        duration_s = 2
        repetitions = 5
        timestamp_vector = np.arange(0.0, duration_s, file.sample_interval_ns / 1e9)

        # values in SI units
        voltages = np.linspace(3.60, 1.90, int(file.samplerate_sps * duration_s))
        currents = np.linspace(100e-6, 2000e-6, int(file.samplerate_sps * duration_s))

        for idx in range(repetitions):
            timestamps = idx * duration_s + timestamp_vector
            file.append_iv_data_si(timestamps, voltages, currents)

    return store_path


@pytest.fixture
def data_h5_path(tmp_path) -> Path:
    return generate_h5_file(tmp_path)


def test_cli_invoke_help():
    res = CliRunner().invoke(
        cli, ["-h"]
    )
    assert res.exit_code == 0


def test_cli_validate_file(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "validate", str(data_h5_path)]
    )
    assert res.exit_code == 0


def test_cli_validate_dir(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "validate", str(data_h5_path.absolute().parent)]
    )
    assert res.exit_code == 0


def test_cli_extract_file_full(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "extract", str(data_h5_path), "--ds-factor", "100", "--separator", ","]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".downsampled_x100.h5").exists()
    assert data_h5_path.with_suffix(".downsampled_x100.data.csv").exists()


def test_cli_extract_file_short(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "extract", str(data_h5_path), "-f", "200", "-s", ";"]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".downsampled_x200.h5").exists()
    assert data_h5_path.with_suffix(".downsampled_x200.data.csv").exists()


def test_cli_extract_file_min(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "extract", str(data_h5_path)]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".downsampled_x1000.h5").exists()
    assert data_h5_path.with_suffix(".downsampled_x1000.data.csv").exists()


def test_cli_extract_dir_full(data_h5_path):
    print(data_h5_path.parent)
    print(data_h5_path.parent.is_dir())
    res = CliRunner().invoke(
        cli, ["-vvv", "extract", str(data_h5_path.parent), "--ds-factor", "2000", "--separator", ";"]
    )
    assert res.exit_code == 0
    #assert data_h5_path.with_suffix(".downsampled_x2000.h5").exists()
    #assert data_h5_path.with_suffix(".downsampled_x2000.data.csv").exists()
    # todo: repair! this works on real shell


def test_cli_extract_meta_file_full(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "extract-meta", str(data_h5_path), "--separator", ";"]
    )
    assert res.exit_code == 0
    # TODO: nothing to grab here, add in base-file, same for tests below


def test_cli_extract_meta_file_short(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "extract-meta", str(data_h5_path), "-s", "-"]
    )
    assert res.exit_code == 0


def test_cli_extract_meta_file_min(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "extract-meta", str(data_h5_path), "-s", "-"]
    )
    assert res.exit_code == 0


def test_cli_extract_meta_dir_full(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "extract-meta", str(data_h5_path.parent), "--separator", ";"]
    )
    assert res.exit_code == 0


def test_cli_downsample_file_full(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "downsample", str(data_h5_path), "--ds-factor", "10"]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".downsampled_x10.h5").exists()


def test_cli_downsample_file_short(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "downsample", str(data_h5_path), "-f", "20"]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".downsampled_x20.h5").exists()


def test_cli_downsample_file_min(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "downsample", str(data_h5_path)]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".downsampled_x5.h5").exists()
    assert data_h5_path.with_suffix(".downsampled_x25.h5").exists()
    assert data_h5_path.with_suffix(".downsampled_x100.h5").exists()


def test_cli_downsample_dir_full(data_h5_path):
    print(data_h5_path.parent)
    print(data_h5_path.parent.is_dir())
    res = CliRunner().invoke(
        cli, ["-vvv", "downsample", str(data_h5_path.parent), "--ds-factor", "40"]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".downsampled_x40.h5").exists()
    # todo: repair! this works on real shell


def test_cli_downsample_rate_file_full(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "downsample", str(data_h5_path), "--sample-rate", "100"]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".downsampled_x1000.h5").exists()


def test_cli_downsample_rate_file_short(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "downsample", str(data_h5_path), "-r", "200"]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".downsampled_x500.h5").exists()


def test_cli_plot_file_full(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "plot", str(data_h5_path), "--start", "0", "--end", "8", "--width", "50", "--height", "10"]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".plot_0s000_to_8s000.png").exists()


def test_cli_plot_file_short(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "plot", str(data_h5_path), "-s", "2.345", "-e", "8.765", "-w", "30", "-h", "20"]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".plot_2s345_to_8s765.png").exists()


def test_cli_plot_file_min(data_h5_path):
    res = CliRunner().invoke(
        cli, ["-vvv", "plot", str(data_h5_path)]
    )
    assert res.exit_code == 0
    assert data_h5_path.with_suffix(".plot_0s000_to_10s000.png").exists()  # full duration of file


def test_cli_plot_dir_min(tmp_path):
    file1_path = generate_h5_file(tmp_path, "hrv_file1.h5")
    file2_path = generate_h5_file(tmp_path, "hrv_file2.h5")
    res = CliRunner().invoke(
        cli, ["-vvv", "plot", str(tmp_path)]
    )
    assert res.exit_code == 0
    assert file1_path.with_suffix(".plot_0s000_to_10s000.png").exists()  # full duration of file
    assert file2_path.with_suffix(".plot_0s000_to_10s000.png").exists()  # full duration of file


def test_cli_multiplot_dir_full(tmp_path):
    generate_h5_file(tmp_path, "hrv_file1.h5")
    generate_h5_file(tmp_path, "hrv_file2.h5")
    res = CliRunner().invoke(
        cli, ["-vvv", "plot", f"'{tmp_path.absolute()}'", "--start", "1", "--end", "7", "--width", "40", "--height", "10", "--multiplot"]
    )
    assert res.exit_code == 0
    assert tmp_path.with_suffix(".multiplot_1s000_to_7s000.png").exists()


def test_cli_multiplot_dir_short(tmp_path):
    generate_h5_file(tmp_path, "hrv_file1.h5")
    generate_h5_file(tmp_path, "hrv_file2.h5")
    res = CliRunner().invoke(
        cli, ["-vvv", "plot", str(tmp_path), "-s", "2.345", "-e", "8.765", "-w", "30", "-h", "20",  "-m"]
    )
    assert res.exit_code == 0
    assert tmp_path.with_suffix(".multiplot_2s345_to_8s765.png").exists()


def test_cli_multiplot_dir_min(tmp_path):
    generate_h5_file(tmp_path, "hrv_file1.h5")
    generate_h5_file(tmp_path, "hrv_file2.h5")
    res = CliRunner().invoke(
        cli, ["-vvv", "plot", str(tmp_path), "-m"]
    )
    assert res.exit_code == 0
    assert tmp_path.with_suffix(".multiplot_0s000_to_10s000.png").exists()  # full duration of file
