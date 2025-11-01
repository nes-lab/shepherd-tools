"""This script converts a IVonne-Recording to shepherd dataformat.

The folder contains a recording from ivonne
-> consisting of voc- & isc-readings with a 50 Hz sampling rate.

Three different file-formats are produced:
- ivsurface / curves -> can be harvested during emulation
- ivtrace / samples -> directly usable for emulation
  (already harvested with two different algorithms)
- isc_voc -> not directly usable (for now)
"""

import os
import sys
from pathlib import Path

from shepherd_data import ivonne
from shepherd_data import mppt

DURATION_MAX = 2 if "PYTEST_CURRENT_TEST" in os.environ else sys.float_info.max
# ⤷ limits runtime for pytest

# config
duration = min(30, DURATION_MAX)

if __name__ == "__main__":
    inp_file_path = Path("./jogging_10m.iv")
    isc_file_path = Path("./jogging_10m_isc_voc.h5")
    ivc_file_path = Path("./jogging_10m_ivcurve.h5")
    voc_file_path = Path("./jogging_10m_ivsample_voc.h5")
    opt_file_path = Path("./jogging_10m_ivsample_opt.h5")

    with ivonne.Reader(inp_file_path) as db:
        db.upsample_2_isc_voc(isc_file_path, duration_s=duration)

        db.convert_2_ivsurface(ivc_file_path, duration_s=duration)

        tr_voc = mppt.OpenCircuitTracker(ratio=0.76)
        tr_opt = mppt.OptimalTracker()

        db.convert_2_ivtrace(voc_file_path, tracker=tr_voc, duration_s=duration)
        db.convert_2_ivtrace(opt_file_path, tracker=tr_opt, duration_s=duration)
