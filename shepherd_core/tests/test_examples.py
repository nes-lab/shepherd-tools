import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def example_path() -> Path:
    path = Path(__file__).absolute().parent.parent / "examples"
    os.chdir(path)
    return path


examples = ["model_tester.py", "vsource_simulation.py", "vharvester_simulation.py"]


@pytest.mark.parametrize("file", examples)
def test_example_scripts(example_path: Path, file: str) -> None:
    subprocess.call(f"python {example_path / file}", shell=True)
