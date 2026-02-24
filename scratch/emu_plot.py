"""Test of possible GPIO-Plotting-Options."""

from datetime import datetime
from pathlib import Path

from matplotlib import pyplot as plt
from shepherd_core.logger import log as logger

from shepherd_data import Reader

files = [Path(__file__).parent / "emu_2026-02-24_13-54-02.h5"]
time_start = 0
time_stop = 10

for file in files:
    with Reader(file, verbose=False) as shpr:
        shpr.plot_to_file(time_start, time_stop, only_pwr=False)
        gpio_names = shpr.get_gpio_pin_names()
        if not isinstance(gpio_names, list):
            continue
        time_zero = shpr.get_time_start()
        if isinstance(time_zero, datetime):
            timestamp = time_zero.timestamp()
        else:
            timestamp = shpr.h5file["gpio"]["time"][0] / 1e9

        fig, axs = plt.subplots(len(gpio_names), sharex=True, sharey=True)  # , layout="tight")
        for _i, gpio_name in enumerate(gpio_names):
            logger.debug("\t .. processing '%s'", gpio_name)
            wfs = shpr.get_gpio_waveforms(gpio_name)
            for gpio_name2, wf in wfs.items():
                gpio_wf = wf.astype(float)
                gpio_wf[:, 0] = gpio_wf[:, 0] / 1e9 - timestamp
                # TODO: filter for time, repair first? we need one more entry on each side
                axs[_i].step(gpio_wf[:, 0], gpio_wf[:, 1], label=gpio_name2)
                axs[_i].set_xlabel("time [s]")
                # axs[_i].set_ylabel("gpio_level [n]")
                axs[_i].get_yaxis().get_major_formatter().set_useOffset(False)
                axs[_i].get_xaxis().get_major_formatter().set_useOffset(False)
                # axs[_i].tick_params(left=False)
                axs[_i].set_yticks([])
        fig.legend()
        fig.suptitle("GPIO-Trace")
        file_img = file.with_suffix(".multiAxis.png")
        if file_img.exists():
            file_img.unlink()
        fig.savefig(file_img)
        plt.close()
