import os
import subprocess
import sys
from pathlib import Path

import pytest

path_example = Path(__file__).resolve().parent.parent / "examples"
path_simulation = Path(__file__).resolve().parent.parent / "examples/simulations"

simulations: list[str] = [
    "vharvester.py",
    "vsource.py",
    "vstorage.py",
]


@pytest.mark.parametrize("file", simulations)
def test_simulation_scripts(file: str) -> None:
    path_file = path_simulation / file
    os.chdir(path_file.parent)
    subprocess.run([sys.executable, path_file.as_posix()], shell=True, check=True)


examples: list[str] = [
    "experiment_generic_var1.py",
    "experiment_models.py",
    "inventory.py",
    "uart_decode_waveform.py",
    "vsource_debug_sim.py",
]


@pytest.mark.parametrize("file", examples)
def test_example_scripts(file: str) -> None:
    path_file = path_example / file
    os.chdir(path_file.parent)
    subprocess.run([sys.executable, path_file.as_posix()], shell=True, check=True)


examples_fw: list[str] = [
    "firmware_model.py",
    "firmware_modification.py",
]


@pytest.mark.converter
@pytest.mark.elf
@pytest.mark.parametrize("file", examples_fw)
def test_example_scripts_fw(file: str) -> None:
    path_file = path_example / file
    os.chdir(path_file.parent)
    subprocess.run([sys.executable, path_file.as_posix()], shell=True, check=True)
