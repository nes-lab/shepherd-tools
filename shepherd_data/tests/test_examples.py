import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def example_path() -> Path:
    path = Path(__file__).absolute().parent.parent / "examples"
    os.chdir(path)
    return path


def test_example_script_1(example_path: Path) -> None:
    path = example_path / "example_convert_ivonne.py"
    subprocess.call(f"python {path}", shell=True)


def test_example_script_2(example_path: Path) -> None:
    path = example_path / "example_extract_logs.py"
    subprocess.call(f"python {path}", shell=True)


def test_example_script_3(example_path: Path) -> None:
    path = example_path / "example_generate_sawtooth.py"
    subprocess.call(f"python {path}", shell=True)


def test_example_script_4(example_path: Path) -> None:
    path = example_path / "example_plot_traces.py"
    subprocess.call(f"python {path}", shell=True)


def test_example_script_5(example_path: Path) -> None:
    path = example_path / "example_repair_recordings.py"
    subprocess.call(f"python {path}", shell=True)
