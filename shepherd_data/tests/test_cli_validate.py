from pathlib import Path

from click.testing import CliRunner

from shepherd_data.cli import cli


def test_cli_validate_file(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["-v", "validate", str(data_h5)])
    assert res.exit_code == 0


def test_cli_validate_dir(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["-v", "validate", str(data_h5.parent)])
    assert res.exit_code == 0
