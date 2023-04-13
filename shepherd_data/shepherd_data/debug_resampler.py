import logging
from pathlib import Path

import shepherd_data as shpd

file = Path("./hrv_sawtooth_1h.h5")
samplerate_sps = 1000

logger = logging.getLogger("SHPData.debug")
logger.setLevel(logging.DEBUG)

with shpd.Reader(file) as shpr:
    out_file = file.with_suffix(f".fs_{samplerate_sps}.h5")
    logger.info(
        "Resampling '%s' from %d Hz to %d Hz ...",
        file.name,
        shpr.samplerate_sps,
        samplerate_sps,
    )
    with shpd.Writer(
        out_file,
        mode=shpr.get_mode(),
        datatype=shpr.get_datatype(),
        window_samples=shpr.get_window_samples(),
        cal_data=shpr.get_calibration_data(),
    ) as shpw:
        shpr.resample(
            shpr.ds_time, shpw.ds_time, samplerate_dst=samplerate_sps, is_time=True
        )
        shpr.resample(shpr.ds_voltage, shpw.ds_voltage, samplerate_dst=samplerate_sps)
        shpr.resample(shpr.ds_current, shpw.ds_current, samplerate_dst=samplerate_sps)
        shpw.save_metadata()
