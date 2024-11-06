from pathlib import Path

from click.testing import CliRunner

from shepherd_data.cli import cli


def test_cli_extract_uart_file_full(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["--verbose", "extract-uart", str(data_h5)])
    assert res.exit_code == 0
    # TODO: nothing to grab here, add in base-file, same for tests below


def test_cli_extract_uart_file_short(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["-v", "extract-uart", str(data_h5)])
    assert res.exit_code == 0


def test_cli_extract_uart_file_min(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["extract-uart", str(data_h5)])
    assert res.exit_code == 0


def test_cli_extract_uart_dir_full(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["--verbose", "extract-meta", str(data_h5.parent)])
    assert res.exit_code == 0
