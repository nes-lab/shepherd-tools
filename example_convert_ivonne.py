from pathlib import Path
import shepherd_data.ivonne as ivonne

# this script converts a IVonne-Recording to shepherd ivcurves
# repo contains a recording from ivonne
# -> consists of voc & isc with 50 Hz sampling rate
# TODO: could also be harvested

if __name__ == "__main__":

    inp_file_path = Path("./jogging_10m.iv")
    out_file_path = Path("./jogging_10m_ivcurves.h5")

    with ivonne.Reader(inp_file_path) as db:
        db.convert_2_ivcurves(out_file_path)
