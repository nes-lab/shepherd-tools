from typing import Optional

import numpy as np
import yaml

from .. import Reader
from .uart import Uart

__all__ = ["Uart"]


def get_pin_log(array: int, pin_num: int) -> bool:
    return ((array >> pin_num) & 0b1) > 0


def get_pin_num(name: str, descriptions: dict) -> Optional[int]:
    for desc_name, desc in descriptions.items():
        if name in desc["name"]:
            return int(desc_name)
    return None


def waveform_to_uart(h5read: Reader) -> np.ndarray:
    gpio_ts = h5read["gpio"]["time"]
    gpio_vs = h5read["gpio"]["value"]
    gpio_desc = yaml.safe_load(h5read["gpio"]["value"].attrs["description"])

    pin_num = get_pin_num("uart", gpio_desc)
    gpio_ps = [get_pin_log(value, pin_num) for value in gpio_vs]

    write_to_file = False
    if write_to_file:
        path_csv = h5read.file_path.with_suffix(f".waveform.pin{pin_num}.csv")
        with open(path_csv, "w") as csv:
            csv.write("timestamp [s],gpio\n")
            for index, value in enumerate(gpio_ps):
                csv.write(f"{gpio_ts[index] / 1e9},{int(value)}\n")

    gpio_wf = np.column_stack((gpio_ts, gpio_ps)).astype(float)
    gpio_wf[:, 0] = gpio_wf[:, 0] / 1e9

    uart = Uart(gpio_wf)
    return uart.get_lines()
