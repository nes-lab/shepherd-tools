import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def example_path() -> Path:
    path = Path(__file__).resolve().parent.parent / "examples"
    os.chdir(path)
    return path


examples = [
    "example_convert_ivonne.py",
    "example_extract_logs.py",
    "example_generate_sawtooth.py",
    "example_plot_traces.py",
    "example_repair_recordings.py",
]


@pytest.mark.parametrize("file", examples)
def test_example_scripts(example_path: Path, file: str) -> None:
    subprocess.run([sys.executable, (example_path / file).as_posix()], shell=True, check=True)
