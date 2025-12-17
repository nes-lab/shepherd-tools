"""Script to convert Bonito recordings to Shepherd Nova EEnvs."""

from pathlib import Path

from convert_v1_eenv import convert as convert_eenv
from shepherd_core.logger import log

DATASETS: dict[dict[str, str | int]] = {
    "bonito_jogging_mixed": {
        "old_name": "jogging_mixed",
        # Omit sheep3 since its recording is broken
        # Its plot looks irregular compared to the other piezo harvesters.
        # A possible cause could be a bad contact.
        "node_glob": "sheep[01245]/jogging.h5",
        "start": 1_621_081_752_600_000_000,
        "duration": int(3505.9 * 1e9),
    },
    "bonito_stairs_solar": {
        "old_name": "data_step",
        "node_glob": "sheep*/rec_sheep*.h5",
        "start": 1579171761700000000,
        "duration": int(3608.1 * 1e9),
    },
    "bonito_office_solar": {
        "old_name": "office_new",
        "node_glob": "sheep*/office_sd.h5",
        "start": 1625124518000000000,
        "duration": int(10798.0 * 1e9),
    },
    "bonito_cars_piezo": {
        "old_name": "cars_convoi",
        "node_glob": "sheep*/cars_convoi.h5",
        "start": 1620739600000000000,
        "duration": int(4687.3 * 1e9),
    },
    "bonito_washer_piezo": {
        "old_name": "washing_machine",
        "node_glob": "sheep*/washing_machine.h5",
        "start": 1620727713000000000,
        "duration": int(3880.2 * 1e9),
    },
    # Add a second version of the washer set as the beginning is rather
    # undynamic. The final 40 minutes which include tumbling are used here.
    "bonito_washer_piezo_tumble_only": {
        "old_name": "washing_machine",
        "node_glob": "sheep*/washing_machine.h5",
        "start": 1620729193200000000,
        "duration": int(2400.0 * 1e9),
    },
}


def convert_bonito_eenvs() -> None:
    """Convert bonito environments according to the DATASETS dict."""
    eenv_dir = Path("./neslab-eh-data").resolve()

    path_here = Path(__file__).parent.absolute()
    if Path("/var/shepherd/").exists():
        output_dir = Path("/var/shepherd/content/eenv/nes_lab/")
    else:
        output_dir = path_here / "content/eenv/nes_lab/"
    output_dir.mkdir(exist_ok=True, parents=True)

    for new_name, params in DATASETS.items():
        basedir = eenv_dir / params["old_name"]
        if not basedir.exists():
            msg = f"directory {basedir!s} does not exist"
            raise RuntimeError(msg)

        files = list(basedir.glob(params["node_glob"]))

        outpath = output_dir / new_name
        if outpath.exists():
            log.warning(f"Output path exists: {outpath}. Skipping environment {new_name}")
            continue
        outpath.mkdir(exist_ok=True)

        convert_eenv(
            input_files=files,
            output_dir=outpath,
            start_ns=params["start"],
            duration_ns=params["duration"],
        )


if __name__ == "__main__":
    convert_bonito_eenvs()
