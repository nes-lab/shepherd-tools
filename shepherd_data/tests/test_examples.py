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
    "convert_ivonne.py",
    "extract_logs.py",
    "generate_sawtooth.py",
    "plot_traces.py",
    "repair_recordings.py",
]


@pytest.mark.parametrize("file", examples)
def test_example_scripts(example_path: Path, file: str) -> None:
    subprocess.run([sys.executable, (example_path / file).as_posix()], shell=True, check=True)
