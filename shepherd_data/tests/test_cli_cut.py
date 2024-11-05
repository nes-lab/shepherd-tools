from pathlib import Path

from click.testing import CliRunner

from shepherd_data.cli import cli


def test_cli_cut_file_full(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["--verbose", "cut", "--start", "1", "--end", "6", str(data_h5)])
    assert res.exit_code == 0
    # TODO: nothing to grab here, add in base-file, same for tests below


def test_cli_cut_file_short(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["-v", "cut", "-s", "2", "-e", "5", str(data_h5)])
    assert res.exit_code == 0


def test_cli_cut_file_min(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["cut", str(data_h5)])
    assert res.exit_code == 0


def test_cli_cut_dir_full(data_h5: Path) -> None:
    res = CliRunner().invoke(
        cli, ["--verbose", "cut", "--start", "3", "--end", "4", str(data_h5.parent)]
    )
    assert res.exit_code == 0
