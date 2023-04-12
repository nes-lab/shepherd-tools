from pathlib import Path

from click.testing import CliRunner

from shepherd_data.cli import cli


def test_cli_downsample_file_full(data_h5: Path) -> None:
    res = CliRunner().invoke(
        cli, ["-vvv", "downsample", "--ds-factor", "10", str(data_h5)]
    )
    assert res.exit_code == 0
    assert data_h5.with_suffix(".downsampled_x10.h5").exists()


def test_cli_downsample_file_short(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["-vvv", "downsample", "-f", "20", str(data_h5)])
    assert res.exit_code == 0
    assert data_h5.with_suffix(".downsampled_x20.h5").exists()


def test_cli_downsample_file_min(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["-vvv", "downsample", str(data_h5)])
    assert res.exit_code == 0
    assert data_h5.with_suffix(".downsampled_x5.h5").exists()
    assert data_h5.with_suffix(".downsampled_x25.h5").exists()
    assert data_h5.with_suffix(".downsampled_x100.h5").exists()


def test_cli_downsample_dir_full(data_h5: Path) -> None:
    print(data_h5.parent)
    print(data_h5.parent.is_dir())
    res = CliRunner().invoke(
        cli, ["-vvv", "downsample", "--ds-factor", "40", str(data_h5.parent)]
    )
    assert res.exit_code == 0
    assert data_h5.with_suffix(".downsampled_x40.h5").exists()


def test_cli_downsample_rate_file_full(data_h5: Path) -> None:
    res = CliRunner().invoke(
        cli, ["-vvv", "downsample", "--sample-rate", "100", str(data_h5)]
    )
    assert res.exit_code == 0
    assert data_h5.with_suffix(".downsampled_x1000.h5").exists()


def test_cli_downsample_rate_file_short(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["-vvv", "downsample", "-r", "200", str(data_h5)])
    assert res.exit_code == 0
    assert data_h5.with_suffix(".downsampled_x500.h5").exists()
