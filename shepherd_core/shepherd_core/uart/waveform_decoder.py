from pathlib import Path
from typing import Optional

import numpy as np

#from ..logger import logger

# TODO:
#
# UART:
# - 1 bit Start (LOW)
# - 1 .. **8** .. 64 bit data-frame  - TODO
# - **1**, 1.5, 2 bit stop (HIGH) - don't care?
# - **no**, even, odd parity bit - TODO
# - **LSB** / MSB first - detectable with dict-compare
# - **no** inversion


def open_csv(path: Path) -> np.ndarray:
    events = np.loadtxt(path.as_posix(), delimiter=",", skiprows=1)
    # np.genfromtxt(path.as_posix(), delimiter=",", names=True)

    # verify table
    if events.shape[1] != 2:
        raise TypeError("Input file should have 2 rows, comma-separated -> timestamp & digital value")
    if events.shape[0] < 8:
        raise TypeError("Input file is too short (< state-changes)")
    # verify timestamps
    time_steps = events[1:, 0] - events[:-1, 0]
    if any(time_steps < 0):
        raise TypeError("Timestamps are not continuous")
    return events


def detect_inversion(events: np.ndarray) -> bool:
    """ analyze bit-state during long pauses (unchanged states)
        - pause should be HIGH for non-inverted mode (default)
        - assumes max frame of 64 bit + 20 for safety
    """
    dur_steps = events[1:, 0] - events[:-1, 0]
    min_step = dur_steps[dur_steps > 0].min()
    pauses = dur_steps > 80 * min_step
    states_1 = events[:-1, 1]
    pause_states = states_1[pauses]
    mean_state = pause_states.mean()
    if 0.1 < mean_state < 0.9:
        raise ValueError("Inversion in pauses could not be detected")
    return mean_state < 0.5


def convert_analog2digital(events: np.ndarray, invert: bool = False) -> np.ndarray:
    """ divide dimension in two, divided by mean-value
    """
    data = events[:, 1]
    mean = np.mean(data)
    if invert:
        events[:, 1] = data <= mean
    else:
        events[:, 1] = data >= mean
    return events


def filter_redundant_states(events: np.ndarray) -> np.ndarray:
    """ sum of two sequential states is always 1 (True + False) if alternating
    """
    data_0 = events[:, 1]
    data_1 = np.concatenate([[not data_0[0]], data_0[:-1]])
    data_f = (data_0 + data_1)
    return events[data_f == 1]


def detect_baudrate(events: np.ndarray) -> int:
    """ analyze the smallest step
    """
    dur_steps = events[1:, 0] - events[:-1, 0]
    min_step = dur_steps[dur_steps > 0].min()
    mean_step = dur_steps[(dur_steps >= min_step) & (dur_steps <= 1.33 * min_step)].mean()
    baudrate = round(1/mean_step)
    return baudrate


def detect_half_stop(events: np.ndarray, baudrate: Optional[int] = None) -> bool:
    """ looks into the spacing between time-steps
    """
    if baudrate is None:
        baudrate = detect_baudrate(events)
    step = 1.0 / baudrate
    return np.sum((events > 1.333 * step) & (events < 1.667 * step)) > 0


def detect_dataframe_length(events: np.ndarray) -> int:
    """ look after longest pauses
        - accumulate steps until a state with uneven step-size is found
    """
    pass


def prepare_events(events: np.ndarray) -> np.ndarray:
    events_bool = convert_analog2digital(events)
    events_clean = filter_redundant_states(events_bool)
    if len(events) > len(events_clean):
        print(f"filtered out {len(events) - len(events_clean)}/{len(events)} events (redundant)")
    ubr = detect_baudrate(events_clean)
    print("detected baud-rate = %d", ubr)
    print(f"found 1.5 stops: {detect_half_stop(events_clean)}")
    inv = detect_inversion(events_clean)
    if inv:
        print("detected inversion -> will invert")
        events_clean = convert_analog2digital(events_clean, invert=True)
    return events_clean


def decode_uart(events: np.ndarray, data_count_n: int = 8, parity: ) -> np.ndarray:
    """
    ways to detect EOF:
    - long pause on HIGH
    - offwidth pause on high
    - bit_pos > max
    """
    dur_steps = events[1:, 0] - events[:-1, 0]
    min_step = dur_steps[dur_steps > 0].min()
    events_n = events[:-1, :]
    events_n[:, 2] = dur_steps / min_step
    # TODO: dset could be divided (long pauses) and threaded for speedup

    pos_df = None
    symbol = 0
    t_start = None
    content = []
    for time, value, steps in events_n:
        if steps > data_count_n:
            if value:  # long pause on High
                if pos_df is not None:
                    content.append([t_start, chr(symbol)])
                    t_start = None
                    symbol = 0
                pos_df = None
            else:
                print("Error - Long pause - but SigLow")
            continue
        off_step = abs(steps - round(steps)) > 0.1
        if pos_df is None and value == 0:
            # Start of frame
            pos_df = 0
            steps -= 1
            t_start = time
        if pos_df is not None:
            if round(steps) >= 1 and value:
                chunk = min(steps, data_count_n - pos_df - 1)
                lshift = min(pos_df, data_count_n - 1)
                symbol += (2**round(chunk) - 1) << lshift
            pos_df += round(steps)
            if pos_df >= data_count_n or (off_step and value):
                if pos_df is not None:
                    content.append([t_start, chr(symbol)])
                    t_start = None
                    symbol = 0
                pos_df = None
                if off_step and value == 0:
                    print("Error - Off-sized step - but SigLow")

    return np.concatenate(content)


#open_csv(Path("uart_raw1.csv"))
uev = open_csv(Path("uart_raw2.csv"))
uev = prepare_events(uev)
text = decode_uart(uev)

