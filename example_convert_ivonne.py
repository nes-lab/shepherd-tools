from pathlib import Path
from datalib_ivonne import convert_ivonne_2_ivcurves

if __name__ == "__main__":

    inp_file_path = Path("./jogging_10m.iv")
    out_file_path = Path("./jogging_10m.h5")

    convert_ivonne_2_ivcurves(inp_file_path, out_file_path)
