"""Script to convert Bonito recordings to Shepherd Nova EEnvs."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from commons import process_mp
from commons import root_storage_default
from convert_v1_eenv import convert_file
from shepherd_core.logger import log

# config

bonito_input_path = Path().cwd() / "neslab-eh-data"

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
        "start": 1_579_171_761_700_000_000,
        "duration": int(3608.1 * 1e9),
    },
    "bonito_office_solar": {
        "old_name": "office_new",
        "node_glob": "sheep*/office_sd.h5",
        "start": 1_625_124_518_000_000_000,
        "duration": int(10798.0 * 1e9),
    },
    "bonito_cars_piezo": {
        "old_name": "cars_convoi",
        "node_glob": "sheep*/cars_convoi.h5",
        "start": 1_620_739_600_000_000_000,
        "duration": int(4687.3 * 1e9),
    },
    "bonito_washer_piezo": {
        "old_name": "washing_machine",
        "node_glob": "sheep*/washing_machine.h5",
        "start": 1_620_727_713_000_000_000,
        "duration": int(3880.2 * 1e9),
    },
    # Add a second version of the washer set as the beginning is rather
    # undynamic. The final 40 minutes which include tumbling are used here.
    "bonito_washer_piezo_tumble_only": {
        "old_name": "washing_machine",
        "node_glob": "sheep*/washing_machine.h5",
        "start": 1_620_729_193_200_000_000,
        "duration": int(2400.0 * 1e9),
    },
}


def get_config_for_workers(
    path_dir: Path = root_storage_default,
) -> list[tuple[Callable, dict[str, Any]]]:
    """Generate worker-configurations for the conversion of bonito recordings.

    The config is a list of tuples. Each containing a
    callable function and a dict with its arguments.

    Convert bonito environments according to the DATASETS dict.
    """
    cfgs: list[tuple[Callable, dict[str, Any]]] = []
    for new_name, params in DATASETS.items():
        input_dir = bonito_input_path / params["old_name"]
        if not input_dir.exists():
            log.error(f"Input-Directory '{input_dir!s}' does not exist -> skipping")
            continue

        files = input_dir.glob(params["node_glob"])

        output_dir = path_dir / "bonito" / new_name
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, input_file in enumerate(files):
            output_file = output_dir / f"node{i}.h5"
            if output_file.exists():
                log.warning(
                    f"Output file '{output_file.name}' exists -> "
                    f"Skipping corresponding input file '{input_file}'"
                )
                continue
            args: dict[str, Any] = {
                "in_file": input_file,
                "out_file": output_file,
                "tstart_ns": params["start"],
                "duration_ns": params["duration"],
            }
            cfgs.append((convert_file, args))
    return cfgs


if __name__ == "__main__":
    process_mp(get_config_for_workers)
