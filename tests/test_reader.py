import sys

import yaml

from shepherd_data import Reader

from .conftest import generate_h5_file


def test_reader_metadata(data_h5_path):
    with Reader(data_h5_path, verbose=True) as sfr:

        assert sfr.energy() > 0
        assert sfr.is_valid()

        meta_data_a = sfr.save_metadata()
        meta_path = data_h5_path.with_suffix(".yml")
        assert meta_path.exists()
        with open(meta_path) as meta_file:
            meta_data_b = yaml.safe_load(meta_file)
            assert len(meta_data_b) == len(meta_data_a)
            assert sys.getsizeof(meta_data_b) == sys.getsizeof(meta_data_a)


# TODO:
#  - confirm energy stays same after resampling
#  - length should also stay same
