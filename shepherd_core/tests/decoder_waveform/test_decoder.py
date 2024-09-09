from pathlib import Path

import pytest

from shepherd_core.decoder_waveform import Uart


@pytest.fixture
def example_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "examples"


def test_decode_uart(example_path: Path) -> None:
    uwd = Uart(example_path / "uart_raw2.csv")
    _ = uwd.get_symbols()
    _ = uwd.get_lines()
    _ = uwd.get_text()


def test_decode_speedup(example_path: Path) -> None:
    uwd = Uart(example_path / "uart_raw2.csv")
    _ = uwd.get_symbols(force_redo=True)
    _ = uwd.get_lines(force_redo=True)
    _ = uwd.get_text(force_redo=True)

    # these now have cached the result
    _ = uwd.get_symbols()
    _ = uwd.get_lines()
    _ = uwd.get_text()


def test_decode_chained(example_path: Path) -> None:
    uwd = Uart(example_path / "uart_raw2.csv")
    _ = uwd.get_text()  # get_symbols() and get_lines() is executed automatically
