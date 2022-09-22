from click.testing import CliRunner

from shepherd_data.cli import cli


def test_cli_validate_file(data_h5_path):
    res = CliRunner().invoke(cli, ["-vvv", "validate", str(data_h5_path)])
    assert res.exit_code == 0


def test_cli_validate_dir(data_h5_path):
    res = CliRunner().invoke(cli, ["-vvv", "validate", str(data_h5_path.parent)])
    assert res.exit_code == 0
