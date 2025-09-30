import os
import subprocess
import sys
from pathlib import Path

import pytest

path_example = Path(__file__).resolve().parent.parent / "examples"
path_simulation = Path(__file__).resolve().parent.parent / "examples/simulations"

simulations: list[Path] = [
    path_simulation / "vharvester.py",
    path_simulation / "vsource.py",
    path_simulation / "vstorage.py",
]


@pytest.mark.parametrize("path_file", simulations)
def test_simulation_scripts(path_file: Path) -> None:
    os.chdir(path_file.parent)
    subprocess.run([sys.executable, path_file.as_posix()], shell=True, check=True)


examples: list[Path] = [
    path_example / "experiment_generic_var1.py",
    path_example / "experiment_models.py",
    path_example / "inventory.py",
    path_example / "uart_decode_waveform.py",
    path_example / "vsource_debug_sim.py",
]


@pytest.mark.parametrize("path_file", examples)
def test_example_scripts(path_file: Path) -> None:
    os.chdir(path_file.parent)
    subprocess.run([sys.executable, path_file.as_posix()], shell=True, check=True)


examples_fw = [
    path_example / "firmware_model.py",
    path_example / "firmware_modification.py",
]


@pytest.mark.converter
@pytest.mark.elf
@pytest.mark.parametrize("path_file", examples_fw)
def test_example_scripts_fw(path_file: Path) -> None:
    os.chdir(path_file.parent)
    subprocess.run([sys.executable, path_file.as_posix()], shell=True, check=True)
