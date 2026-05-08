"""Test of possible GPIO-Plotting-Options."""

from datetime import datetime
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from shepherd_core.logger import log as logger

from shepherd_data import Reader

files = [
    Path(__file__).parent / "sheep05.h5",
]
time_start = 4
time_stop = 10

def extract_gpio_data(self, time_start, time_stop) -> dict[str, np.ndarray] | None:
    gpio_names = self.get_gpio_pin_names()
    if not isinstance(gpio_names, list):
        return None
    time_zero = shpr.get_time_start()
    if isinstance(time_zero, datetime):
        timestamp = time_zero.timestamp()
    else:
        timestamp = shpr.h5file["gpio"]["time"][0] / 1e9

    result_data: dict[str, np.ndarray] = {}
    for gpio_name in gpio_names:
        logger.info("\t .. processing '%s'", gpio_name)
        wfs = shpr.get_gpio_waveforms(gpio_name)
        for gpio_name2, wf in wfs.items():
            # prepare time-format
            gpio_wf = wf.astype(float)
            gpio_wf[:, 0] = gpio_wf[:, 0] / 1e9 - timestamp
            # prevent empty
            if len(gpio_wf) < 1:
                logger.warning(" ... was empty")
                gpio_wf = np.array([[0, 0]])
            # filter time-slot, also add padding to fix incomplete drawing
            idx_start = np.searchsorted(gpio_wf[:, 0], time_start, side="left")
            idx_stop = np.searchsorted(gpio_wf[:, 0], time_stop, side="left")
            if idx_start < 1:
                gpio_wf = np.vstack([gpio_wf[0], gpio_wf])
                idx_start += 1
                idx_stop += 1
            if idx_stop >= len(gpio_wf) - 1:
                gpio_wf = np.vstack([gpio_wf, gpio_wf[-1]])
            gpio_wf = gpio_wf[idx_start - 1 : idx_stop + 1]
            gpio_wf[0, 0] = time_start
            gpio_wf[-1, 0] = time_stop
            result_data[gpio_name2] = gpio_wf
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
        ts_start = datetime.now()
        data = extract_gpio_data(shpr, time_start, time_stop)
        duration = datetime.now() - ts_start
        logger.info(f"prep took {duration.total_seconds()} seconds")
        if data is None:
            continue
    ts_start = datetime.now()
    plot_gpio_data(data)
    duration = datetime.now() - ts_start
    logger.info(f"plot took {duration.total_seconds()} seconds")




