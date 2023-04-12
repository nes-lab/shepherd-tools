from pathlib import Path

from click.testing import CliRunner

from shepherd_data.cli import cli


def test_cli_extract_file_full(data_h5: Path) -> None:
    res = CliRunner().invoke(
        cli,
        [
            "-vvv",
            "extract",
            "--ds-factor",
            "100",
            "--separator",
            ",",
            str(data_h5),
        ],
    )
    assert res.exit_code == 0
    assert data_h5.with_suffix(".downsampled_x100.h5").exists()
    assert data_h5.with_suffix(".downsampled_x100.data.csv").exists()


def test_cli_extract_file_short(data_h5: Path) -> None:
    res = CliRunner().invoke(
        cli, ["-vvv", "extract", "-f", "200", "-s", ";", str(data_h5)]
    )
    assert res.exit_code == 0
    assert data_h5.with_suffix(".downsampled_x200.h5").exists()
    assert data_h5.with_suffix(".downsampled_x200.data.csv").exists()


def test_cli_extract_file_min(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["-vvv", "extract", str(data_h5)])
    assert res.exit_code == 0
    assert data_h5.with_suffix(".downsampled_x1000.h5").exists()
    assert data_h5.with_suffix(".downsampled_x1000.data.csv").exists()


def test_cli_extract_dir_full(data_h5: Path) -> None:
    print(data_h5.parent)
    print(data_h5.parent.is_dir())
    res = CliRunner().invoke(
        cli,
        [
            "-vvv",
            "extract",
            "--ds-factor",
            "2000",
            "--separator",
            ";",
            str(data_h5.parent),
        ],
    )
    assert res.exit_code == 0
    assert data_h5.with_suffix(".downsampled_x2000.h5").exists()
    assert data_h5.with_suffix(".downsampled_x2000.data.csv").exists()


def test_cli_extract_meta_file_full(data_h5: Path) -> None:
    res = CliRunner().invoke(
        cli, ["-vvv", "extract-meta", "--separator", ";", str(data_h5)]
    )
    assert res.exit_code == 0
    # TODO: nothing to grab here, add in base-file, same for tests below


def test_cli_extract_meta_file_short(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["-vvv", "extract-meta", "-s", "-", str(data_h5)])
    assert res.exit_code == 0


def test_cli_extract_meta_file_min(data_h5: Path) -> None:
    res = CliRunner().invoke(cli, ["-vvv", "extract-meta", "-s", "-", str(data_h5)])
    assert res.exit_code == 0


def test_cli_extract_meta_dir_full(data_h5: Path) -> None:
    res = CliRunner().invoke(
        cli, ["-vvv", "extract-meta", "--separator", ";", str(data_h5.parent)]
    )
    assert res.exit_code == 0
