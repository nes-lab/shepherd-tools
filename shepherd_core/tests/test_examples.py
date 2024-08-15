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
    "experiment_generic_var1.py",
    "experiment_models.py",
    "inventory.py",
    "uart_decode_waveform.py",
    "simulate_vharvester.py",
    "simulate_vsource.py",
    "vsource_debug_sim.py",
]


@pytest.mark.parametrize("file", examples)
def test_example_scripts(example_path: Path, file: str) -> None:
    subprocess.run([sys.executable, (example_path / file).as_posix()], shell=True, check=True)


examples_fw = [
    "firmware_model.py",
    "firmware_modification.py",
]


@pytest.mark.converter
@pytest.mark.elf
@pytest.mark.parametrize("file", examples_fw)
def test_example_scripts_fw(example_path: Path, file: str) -> None:
    subprocess.run([sys.executable, (example_path / file).as_posix()], shell=True, check=True)
