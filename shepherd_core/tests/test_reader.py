import sys
from pathlib import Path

import h5py
import pytest
import yaml

from shepherd_core import Reader
from shepherd_core import Writer


def test_reader_metadata(data_h5: Path) -> None:
    with Reader(data_h5, verbose=True) as sfr:
        assert sfr.energy() > 0
        assert sfr.is_valid()

        meta_data_a = sfr.save_metadata()
        meta_path = data_h5.resolve().with_suffix(".yaml")
        assert meta_path.exists()
        with meta_path.open() as meta_file:
            meta_data_b = yaml.safe_load(meta_file)
            assert len(meta_data_b) == len(meta_data_a)
            assert sys.getsizeof(meta_data_b) == sys.getsizeof(meta_data_a)


def test_reader_items(data_h5: Path) -> None:
    """Access internal"""
    with Reader(data_h5, verbose=True) as sfr:
        _ = sfr["data"]  # group
        _ = sfr["mode"]  # attribute
        with pytest.raises(KeyError):
            _ = sfr["non-existing"]


def test_reader_open(tmp_path: Path) -> None:
    with pytest.raises(TypeError):
        Reader(file_path=None)

    tmp_file = (tmp_path / "data.h5").resolve()

    with pytest.raises(FileNotFoundError):
        Reader(file_path=tmp_file)

    with tmp_file.open("w") as tf:
        tf.write("abc def ghi")
    with pytest.raises(TypeError):
        Reader(file_path=tmp_file)


def test_reader_meta_repr(data_h5: Path) -> None:
    with Reader(data_h5, verbose=True) as sfr:
        print(sfr)
        print(sfr.get_calibration_data())
        print(sfr.get_hrv_config())


def test_reader_read_open_end(data_h5: Path) -> None:
    with Reader(data_h5, verbose=True) as sfr:
        for buf in sfr.read_buffers():
            print(len(buf[0]))


def test_reader_read_5(data_h5: Path) -> None:
    with Reader(data_h5, verbose=True) as sfr:
        for buf in sfr.read_buffers(end_n=5):
            print(len(buf[0]))


def test_reader_read_start_late(data_h5: Path) -> None:
    with Reader(data_h5, verbose=True) as sfr:
        for buf in sfr.read_buffers(start_n=2):
            print(len(buf[0]))


def test_reader_read_raw(data_h5: Path) -> None:
    with Reader(data_h5, verbose=True) as sfr:
        for buf in sfr.read_buffers(is_raw=True):
            print(len(buf[0]))


def test_reader_non_valid(tmp_path: Path) -> None:
    data_h5 = tmp_path / "data.h5"
    with h5py.File(data_h5, "w") as h5f:
        grp_data = h5f.create_group("data")
        grp_data.create_dataset("time", (0,))
        grp_data.create_dataset("current", (0,))
        grp_data.create_dataset("voltage", (0,))
        grp_data["time"].attrs["gain"] = 1
        grp_data["current"].attrs["gain"] = 1
        grp_data["voltage"].attrs["gain"] = 1
        grp_data["time"].attrs["offset"] = 0
        grp_data["current"].attrs["offset"] = 0
        grp_data["voltage"].attrs["offset"] = 0
    with Reader(data_h5, verbose=True) as sfr:
        # try getting metadata -> no exception but safe defaults
        sfr.get_window_samples()
        sfr.get_mode()
        sfr.get_mode()
        sfr.get_hostname()
        sfr.get_datatype()
        assert not sfr.is_valid()


def test_reader_fault_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Reader(tmp_path, verbose=True)


def test_reader_fault_no_data(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        del sfw.h5file["data"]
    with pytest.raises(KeyError):
        Reader(data_h5, verbose=True)


def test_reader_fault_no_mode(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        del sfw.h5file.attrs["mode"]
    with Reader(data_h5, verbose=True) as sfr:
        assert not sfr.is_valid()


def test_reader_fault_fake_mode(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        sfw.h5file.attrs["mode"] = "burning"
    with Reader(data_h5, verbose=True) as sfr:
        assert not sfr.is_valid()


def test_reader_fault_no_window_samples(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        del sfw.h5file["data"].attrs["window_samples"]
    with Reader(data_h5, verbose=True) as sfr:
        assert not sfr.is_valid()


def test_reader_fault_no_datatype(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        del sfw.h5file["data"].attrs["datatype"]
    with Reader(data_h5, verbose=True) as sfr:
        assert not sfr.is_valid()


def test_reader_fault_wrong_datatype(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        sfw.h5file["data"].attrs["datatype"] = "apples"
    with Reader(data_h5, verbose=True) as sfr:
        assert not sfr.is_valid()


def test_reader_fault_wrong_window1(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        sfw["data"].attrs["datatype"] = "ivcurve"
        sfw["data"].attrs["window_samples"] = 0
    with Reader(data_h5, verbose=True) as sfr:
        assert not sfr.is_valid()


def test_reader_fault_wrong_window2(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        sfw["data"].attrs["datatype"] = "ivsample"
        sfw["data"].attrs["window_samples"] = 1111
    with Reader(data_h5, verbose=True) as sfr:
        # only triggers warning
        assert sfr.is_valid()


def test_reader_fault_no_current(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        del sfw.h5file["data"]["current"]
    with pytest.raises(KeyError):
        Reader(data_h5, verbose=True)


def test_reader_fault_no_voltage(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        del sfw.h5file["data"]["voltage"]
    with pytest.raises(KeyError):
        Reader(data_h5, verbose=True)


def test_reader_fault_non_eq_time(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        sfw.h5file["data"]["time"].resize((0,))
    with Reader(data_h5, verbose=True) as sfr:
        assert sfr.is_valid()
        # soft-criteria ... reader just complains


def test_reader_fault_unaligned(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        new_size = sfw.samples_per_buffer / 2
        sfw.h5file["data"]["time"].resize((new_size,))
        sfw.h5file["data"]["voltage"].resize((new_size,))
        sfw.h5file["data"]["current"].resize((new_size,))
    with Reader(data_h5, verbose=True) as sfr:
        assert sfr.is_valid()
        # soft-criteria ... reader just complains


def test_reader_fault_strange_compression(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        time = sfw.h5file["data"]["time"][:]
        del sfw.h5file["data"]["time"]
        sfw.h5file["data"].create_dataset(
            "time",
            (0,),
            dtype="u8",
            maxshape=(None,),
            compression="lzf",  # something like szip wanted
        )
        sfw.h5file["data"]["time"].resize(time.shape)
        sfw.h5file["data"]["time"][0 : time.shape[0]] = time[: time.shape[0]]
        sfw.h5file["data"]["time"].attrs["gain"] = 1
        sfw.h5file["data"]["time"].attrs["offset"] = 0
    with Reader(data_h5, verbose=True) as sfr:
        assert sfr.is_valid()
        # soft-criteria ... reader just complains


def test_reader_fault_slow_compression(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        time = sfw.h5file["data"]["time"][:]
        del sfw.h5file["data"]["time"]
        sfw.h5file["data"].create_dataset(
            "time",
            (0,),
            dtype="u8",
            maxshape=(None,),
            compression="gzip",
            compression_opts=9,
        )
        sfw.h5file["data"]["time"].resize(time.shape)
        sfw.h5file["data"]["time"][0 : time.shape[0]] = time[: time.shape[0]]
        sfw.h5file["data"]["time"].attrs["gain"] = 1
        sfw.h5file["data"]["time"].attrs["offset"] = 0
    with Reader(data_h5, verbose=True) as sfr:
        assert sfr.is_valid()
        # soft-criteria ... reader just complains


def test_reader_fault_no_hostname(data_h5: Path) -> None:
    with Writer(data_h5, modify_existing=True) as sfw:
        sfw.h5file.attrs["hostname"] = "unknown"
    with Reader(data_h5, verbose=True) as sfr:
        assert sfr.is_valid()
        # soft-criteria ... reader just complains


def test_reader_fault_jumps_timestamp(data_h5: Path) -> None:
    with Reader(data_h5, verbose=True) as sfr:
        assert sfr.check_timediffs()
    with Writer(data_h5, modify_existing=True) as sfw:
        sfw.h5file["data"]["time"][sfw.samples_per_buffer] = 0
    with Reader(data_h5, verbose=True) as sfr:
        assert not sfr.check_timediffs()


def test_reader_save_meta(data_h5: Path) -> None:
    with Reader(data_h5, verbose=True) as sfr:
        assert sfr.save_metadata() != {}
        # yaml now already exists
        assert sfr.save_metadata() == {}


def test_reader_save_meta_fail(data_h5: Path) -> None:
    with Reader(data_h5, verbose=True) as sfr:
        sfr.file_path = None
        assert sfr.save_metadata() == {}
