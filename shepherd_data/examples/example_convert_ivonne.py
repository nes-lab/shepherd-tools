"""this repo contains a recording from ivonne
-> consists of voc & isc with 50 Hz sampling rate

this script converts a IVonne-Recording to shepherd dataformat:
- ivcurves that can be harvested during emulation
- ivsamples that can be directly used for emulation
  (already harvested with to different algorithms)
- isc_voc not directly usable (for now)
"""

from pathlib import Path

from shepherd_data import ivonne
from shepherd_data import mppt

# config
duration = 30

if __name__ == "__main__":
    inp_file_path = Path("./jogging_10m.iv")
    isc_file_path = Path("./jogging_10m_isc_voc.h5")
    ivc_file_path = Path("./jogging_10m_ivcurve.h5")
    voc_file_path = Path("./jogging_10m_ivsample_voc.h5")
    opt_file_path = Path("./jogging_10m_ivsample_opt.h5")

    with ivonne.Reader(inp_file_path) as db:
        db.upsample_2_isc_voc(isc_file_path, duration_s=duration)

        db.convert_2_ivcurves(ivc_file_path, duration_s=duration)

        tr_voc = mppt.OpenCircuitTracker(ratio=0.76)
        tr_opt = mppt.OptimalTracker()

        db.convert_2_ivsamples(voc_file_path, tracker=tr_voc, duration_s=duration)
        db.convert_2_ivsamples(opt_file_path, tracker=tr_opt, duration_s=duration)
