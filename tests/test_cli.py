
import pytest
from shepherd_data import Reader, Writer
from shepherd_data.cli import cli


@pytest.fixture
def data_h5(tmp_path):
    store_path = tmp_path / "harvest_example.h5"
    with Writer(store_path, CalibrationData.from_default()) as store:
        for i in range(100):
            len_ = 10_000
            fake_data = DataBuffer(random_data(len_), random_data(len_), i)
            store.write_buffer(fake_data)
    return store_path
