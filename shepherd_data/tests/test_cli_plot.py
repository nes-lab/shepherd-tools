from pathlib import Path

from click.testing import CliRunner

from shepherd_data.cli import cli

from .conftest import generate_h5_file


def test_cli_plot_file_full(data_h5: Path) -> None:
    res = CliRunner().invoke(
        cli,
        [
            "--verbose",
            "plot",
            "--start",
            "0",
            "--end",
            "8",
            "--width",
            "50",
            "--height",
            "10",
            str(data_h5),
        ],
    )
    assert res.exit_code == 0
    assert data_h5.with_suffix(".plot_0s000_to_8s000.png").exists()


def test_cli_plot_file_short(data_h5: Path) -> None:
    res = CliRunner().invoke(
        cli,
        [
            "-v",
            "plot",
            "-s",
            "2.345",
            "-e",
            "8.765",
            "-w",
            "30",
            "-h",
            "20",
            str(data_h5),
        ],
    )
    assert res.exit_code == 0
    assert data_h5.with_suffix(".plot_2s345_to_8s765.png").exists()


def test_cli_plot_file_min(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["-v", "plot", str(data_h5)])
    assert res.exit_code == 0
    assert data_h5.with_suffix(".plot_0s000_to_10s000.png").exists()  # full duration of file


def test_cli_plot_dir_min(tmp_path: Path) -> None:
    file1_path = generate_h5_file(tmp_path, "hrv_file1.h5")
    file2_path = generate_h5_file(tmp_path, "hrv_file2.h5")
    res = CliRunner().invoke(cli, ["-v", "plot", str(tmp_path.resolve())])
    assert res.exit_code == 0
    assert file1_path.with_suffix(".plot_0s000_to_10s000.png").exists()  # full duration of file
    assert file2_path.with_suffix(".plot_0s000_to_10s000.png").exists()  # full duration of file


def test_cli_multiplot_dir_full(tmp_path: Path) -> None:
    generate_h5_file(tmp_path, "hrv_file1.h5")
    generate_h5_file(tmp_path, "hrv_file2.h5")
    res = CliRunner().invoke(
        cli,
        [
            "--verbose",
            "plot",
            "--start",
            "1",
            "--end",
            "7",
            "--width",
            "40",
            "--height",
            "10",
            "--multiplot",
            str(tmp_path),
        ],
    )
    assert res.exit_code == 0
    assert tmp_path.with_suffix(".multiplot_1s000_to_7s000.png").exists()


def test_cli_multiplot_dir_short(tmp_path: Path) -> None:
    generate_h5_file(tmp_path, "hrv_file1.h5")
    generate_h5_file(tmp_path, "hrv_file2.h5")
    res = CliRunner().invoke(
        cli,
        [
            "-v",
            "plot",
            "-s",
            "2.345",
            "-e",
            "8.765",
            "-w",
            "30",
            "-h",
            "20",
            "-m",
            str(tmp_path),
        ],
    )
    assert res.exit_code == 0
    assert tmp_path.with_suffix(".multiplot_2s345_to_8s765.png").exists()


def test_cli_multiplot_dir_min(tmp_path: Path) -> None:
    generate_h5_file(tmp_path, "hrv_file1.h5")
    generate_h5_file(tmp_path, "hrv_file2.h5")
    res = CliRunner().invoke(cli, ["-v", "plot", "-m", str(tmp_path)])
    assert res.exit_code == 0
    assert tmp_path.with_suffix(".multiplot_0s000_to_10s000.png").exists()  # full duration of file
