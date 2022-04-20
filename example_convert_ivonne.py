from pathlib import Path

from datalib_ivonne import convert_ivonne_2_ivcurves

# this script converts a IVonne-Recording to shepherd ivcurves
# repo contains a recording from ivonne
# -> consists of voc & isc with 50 Hz sampling rate
# TODO: could also be harvested

if __name__ == "__main__":

    inp_file_path = Path("./jogging_10m.iv")
    out_file_path = Path("./jogging_10m_ivcurves.h5")

    convert_ivonne_2_ivcurves(inp_file_path, out_file_path)

