from pathlib import Path

from click.testing import CliRunner

from shepherd_data.cli import cli


def test_cli_version_full() -> None:
    res = CliRunner().invoke(cli, ["-v", "version"])
    assert res.exit_code == 0


def test_cli_version_min(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["version"])
    assert res.exit_code == 0
