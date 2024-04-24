"""Demonstrates decoding of a sampled waveform to UART-symbols."""

from pathlib import Path
from timeit import timeit

from shepherd_core import logger
from shepherd_core.decoder_waveform import Uart

# file captured with logic analyzer, 15.5k events (2700 symbols, 61 lines)
trace = Path(__file__).parent / "uart_raw2.csv"
uwd = Uart(trace)

sym = uwd.get_symbols()
lne = uwd.get_lines()
txt = uwd.get_text()
logger.info(txt)

do_analysis = False
if do_analysis:
    l0 = timeit("Uart(trace)", globals=globals(), number=1000)
    l1 = timeit("uwd.get_symbols(force_redo=True)", globals=globals(), number=100)
    l2 = timeit("uwd.get_lines(force_redo=True)", globals=globals(), number=1000)
    l3 = timeit("uwd.get_text(force_redo=True)", globals=globals(), number=1000)
    print("t_init\t", l0)
    print("t_symb\t", l1 * 10)
    print("t_line\t", l2)
    print("t_text\t", l3)
    # Results:
    # t_init  5.8   [ms/run]
    # t_symb  70.4  [!!!!!]
    # t_line  3.9
    # t_text  0.1
