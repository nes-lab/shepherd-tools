
import pytest
import numpy as np

from shepherd_data import Reader, Writer
from shepherd_data.cli import cli


def random_data(length):
    return np.random.randint(0, high=2 ** 18, size=length, dtype="u4")


@pytest.fixture
def data_h5(tmp_path):
    store_path = tmp_path / "harvest_example.h5"

    with Writer(store_path, compression=1) as file:

        file.set_hostname("artificial")

        duration_s = 10
        repetitions = 4
        timestamp_vector = np.arange(0.0, duration_s, file.sample_interval_ns / 1e9)

        # values in SI units
        voltages = np.linspace(3.60, 1.90, int(file.samplerate_sps * duration_s))
        currents = np.linspace(100e-6, 2000e-6, int(file.samplerate_sps * duration_s))

        for idx in range(repetitions):
            timestamps = idx * duration_s + timestamp_vector
            file.append_iv_data_si(timestamps, voltages, currents)

    return store_path
