"""Test of possible GPIO-Plotting-Options."""

from datetime import datetime
from pathlib import Path

import numpy as np
from dateutil.tz import UTC
from matplotlib import pyplot as plt
from shepherd_core.logger import log as logger

from shepherd_data import Reader

files = [
    Path(__file__).parent / "sheep05.h5",
]
time_start = 4
time_stop = 10


def extract_gpio_data(self, start_s: float, end_s: float) -> dict[str, np.ndarray] | None:
    gpio_names = self.get_gpio_pin_names()
    if not isinstance(gpio_names, list):
        return None

    if not isinstance(start_s, (float, int)):
        start_s = 0
    if not isinstance(end_s, (float, int)):
        end_s = self.runtime_s  # TODO: this is from iv-samples, can be missing
    start_s = max(0, start_s)
    end_s = min(self.runtime_s, end_s)

    time_zero = shpr.get_time_start()
    if isinstance(time_zero, datetime):
        timestamp_zero = time_zero.timestamp()
    else:
        timestamp_zero = float(shpr.h5file["gpio"]["time"][0]) / 1e9
    timestamp_start_ns = int((timestamp_zero + start_s) * 1e9)
    timestamp_stop_ns = int((timestamp_zero + end_s) * 1e9)

    result_data: dict[str, np.ndarray] = {}

    # TODO: could also plot just a subset of GPIOs
    # TODO: the slowness is in .get_gpio_waveforms()
    wfs = shpr.get_gpio_waveforms()
    for gpio_name, wf in wfs.items():
        logger.info("\t .. processing '%s'", gpio_name)
        if len(wf) < 1: # prevent empty
            logger.warning(" ... was empty")
            continue
            # gpio_wf = np.array([[0, 0]])
        # filter time-slot, also add padding to fix incomplete drawing of sparse waveforms
        idx_start = np.searchsorted(wf[:, 0], timestamp_start_ns, side="left")
        idx_stop = idx_start + np.searchsorted(wf[idx_start:, 0], timestamp_stop_ns, side="right")
        pad_start = wf[0] if idx_start < 1 else wf[idx_start - 1]
        pad_end = wf[-1] if (idx_stop > len(wf)) else wf[idx_stop - 1]
        # TODO: can be simplified, when stop-search switches to side=right
        gpio_wf = np.vstack([pad_start, wf[idx_start:idx_stop], pad_end])
        # convert time-format
        # TODO: only if relative is wanted
        gpio_wf = gpio_wf.astype(float)
        gpio_wf[:, 0] = gpio_wf[:, 0] / 1e9 - timestamp_zero
        gpio_wf[0, 0] = start_s
        gpio_wf[-1, 0] = end_s
        result_data[gpio_name] = gpio_wf
    return result_data


def plot_gpio_data(data: dict[str, np.ndarray], *, show_gui: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(18, 8), layout="tight")
    gpio_count = len(data)
    # TODO: for multiplot the gpio-list order has to be fixed and global
    for _i, gpio_name in enumerate(data):
        gpio_wf = data.get(gpio_name)
        if gpio_wf is None:
            continue
        # arrange waveforms on single plot
        y_offset = 1.2 * (gpio_count - _i - 1)
        gpio_wf[:, 1] = gpio_wf[:, 1] + y_offset
        ax.step(gpio_wf[:, 0], gpio_wf[:, 1], label=gpio_name)
        x_offset = time_start + 0.02 * (time_stop - time_start)
        plt.text(x_offset, y_offset + 0.4, gpio_name, size="medium", alpha=0.7)

    ax.set_ylim(-0.2, 1.2 * gpio_count + 0.2)
    ax.set_xlabel("time [s]")
    ax.set_ylabel("gpio_level [n]")
    ax.get_yaxis().get_major_formatter().set_useOffset(False)
    ax.get_xaxis().get_major_formatter().set_useOffset(False)
    ax.set_yticks([])
    fig.suptitle("GPIO-Trace")

    file_img = file.with_suffix(".singleAxis.png")
    if file_img.exists():  # TODO: do NOT just erase data in final version
        file_img.unlink()
    fig.savefig(file_img)
    if show_gui:
        plt.ion()
        plt.show(block=True)
    plt.close()


for file in files:
    with Reader(file, verbose=False) as shpr:
        ts_start = datetime.now(tz=UTC)
        data = extract_gpio_data(shpr, time_start, time_stop)
        duration = datetime.now(tz=UTC) - ts_start
        logger.info(f"prep took {duration.total_seconds()} seconds")
        if data is None:
            continue
    ts_start = datetime.now(tz=UTC)
    plot_gpio_data(data)
    duration = datetime.now(tz=UTC) - ts_start
    logger.info(f"plot took {duration.total_seconds()} seconds")
