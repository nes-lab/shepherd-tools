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
    path = example_path / "model_tester.py"
    subprocess.call(f"python {path}", shell=True)
