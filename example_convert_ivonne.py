from pathlib import Path
import shepherd_data.ivonne as ivonne
import shepherd_data.mppt as mppt

# this repo contains a recording from ivonne
# -> consists of voc & isc with 50 Hz sampling rate

# this script converts a IVonne-Recording to shepherd dataformat:
# - ivcurves that can be harvested during emulation
# - ivsamples that can be directly used for emulation (already harvested with to different algorithms)
# - isc_voc not directly usable (for now)

if __name__ == "__main__":

    inp_file_path = Path("./jogging_10m.iv")
    isc_file_path = Path("./jogging_10m_isc_voc.h5")
    ivc_file_path = Path("./jogging_10m_ivcurves.h5")
    voc_file_path = Path("./jogging_10m_ivsamples_voc.h5")
    opt_file_path = Path("./jogging_10m_ivsamples_opt.h5")

    with ivonne.Reader(inp_file_path) as db:
        db.upsample_2_isc_voc(isc_file_path)

        db.convert_2_ivcurves(ivc_file_path)

        tr_voc = mppt.OpenCircuitTracker(ratio=0.76)
        tr_opt = mppt.OptimalTracker()

        db.convert_2_ivsamples(voc_file_path, tracker=tr_voc)
        db.convert_2_ivsamples(opt_file_path, tracker=tr_opt)
