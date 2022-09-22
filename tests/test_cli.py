from click.testing import CliRunner

from shepherd_data.cli import cli


def test_cli_invoke_help():
    res = CliRunner().invoke(cli, ["-h"])
    assert res.exit_code == 0
