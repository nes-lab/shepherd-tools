from pathlib import Path
from typing import Optional
from typing import Union

import numpy as np

from shepherd_data import Reader
from shepherd_data import Writer


def generate_shp_file(
    store_path: Path,
    mode: Optional[str] = None,
    datatype: Optional[str] = None,
    window_samples: Optional[int] = None,
    cal_data: Optional[dict] = None,
    config: Optional[dict] = None,
    compression: Union[str, int, None] = "default",
    hostname: str = "unknown",
):
    if config is None:
        config = {}
    with Writer(
        store_path,
        mode=mode,
        datatype=datatype,
        window_samples=window_samples,
        cal_data=cal_data,
        compression=compression,
        verbose=True,
    ) as file:
        file.set_hostname(hostname)
        file.set_config(config)
        duration_s = 2
        timestamps = np.arange(0.0, duration_s, file.sample_interval_ns / 1e9)
        voltages = np.linspace(3.60, 1.90, int(file.samplerate_sps * duration_s))
        currents = np.linspace(100e-6, 2000e-6, int(file.samplerate_sps * duration_s))
        file.append_iv_data_si(timestamps, voltages, currents)


def test_writer_basics(tmp_path: Path) -> None:
    store_path = tmp_path / "hrv_test.h5"
    generate_shp_file(store_path)
    with Reader(store_path, verbose=True) as file:
        assert round(file.runtime_s) == 2
        assert file.get_window_samples() == 0
        assert file.get_mode() == "harvester"
        assert file.get_config() == {}
        assert file.get_datatype() == "ivsample"
        assert file.get_hostname() == "unknown"


def test_writer_compression_1(tmp_path: Path) -> None:
    store_path = tmp_path / "hrv_test.h5"
    generate_shp_file(store_path, compression=1)


# TODO:
#  - test writing different and confirming them
#  - different compressions and their size relative to each other
#  - also invalid
#  - read raw-data
