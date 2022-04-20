from pathlib import Path
from datalib import ShepherdReader

# script will:
# - generate plots with various zoom-levels for h5-files
# - note: let the generator- and converter-example run before

if __name__ == "__main__":

    with ShepherdReader(Path("./hrv_sawtooth_1h.h5")) as db:
        db.plot_to_file()
        db.plot_to_file(0, 500)
        db.plot_to_file(0, 80)

    with ShepherdReader(Path("./jogging_10m_ivcurves.h5")) as db:
        db.plot_to_file()
        db.plot_to_file(0, 100)
        db.plot_to_file(0, 10)
        db.plot_to_file(0, 1)
        db.plot_to_file(0, .2)
        db.plot_to_file(0.199, 0.201)
