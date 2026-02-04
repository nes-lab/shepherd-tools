"""Script to convert Bonito recordings to Shepherd Nova EEnvs."""

from collections.abc import Callable
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path
from typing import Any

import yaml
from commons import process_mp
from commons import root_storage_default
from convert_v1_eenv import convert_file
from shepherd_core.data_models import EnergyEnvironment
from shepherd_core.data_models import EnergyProfile
from shepherd_core.data_models import Wrapper
from shepherd_core.logger import log

# config

path_bonito_input: Path = Path().cwd() / "neslab-eh-data"
path_file: Path = Path(__file__)

DATASETS: dict[str, dict[str, Any]] = {
    "bonito_jogging_mixed": {
        "old_name": "jogging_mixed",
        # Omit sheep3 since its recording is broken
        # Its plot looks irregular compared to the other piezo harvesters.
        # A possible cause could be a bad contact.
        "node_glob": "sheep[01245]/jogging.h5",
        "start": 1_621_081_752_600_000_000,
        "timezone": timezone(timedelta(hours=2), "CEST"),
        "duration": int(3505.9 * 1e9),
        "description": (
            "Jogging tour of two people in a public park with solar and vibration harvesting. "
            "Includes short walking and standing breaks. "
            "This was recording in spring time on an early afternoon in Berlin. "
            "The nodes were powered with a powerbank and synchronized via GPS."
        ),
        "metadata": {
            "location": "Europe, Germany, Berlin, H942+CX",
            "coordinates": "N 52.556585, E 13.3554427",
            "route": "https://maps.app.goo.gl/qjWAJeZZfLec4cCE8 (there and back)",
            "energy type": "light & kinetic",
            "energy source": "natural direct & indirect sun light, human body movement",
            "transducer": "IXYS KXOB25-05X3F (PV), Mide S128-J1FR-1808YB (piezo)",
            "node0": "person 1, piezo, left ankle",
            "node1": "person 1, solar, left wrist",
            "node2": "person 1, piezo, right ankle",
            # sheep 3 scrapped
            "node3": "person 2, solar, left wrist",
            "node4": "person 2, piezo, right ankle",
            # duration & TS are later derived from main data
        },
    },
    "bonito_stairs_solar": {
        "old_name": "data_step",
        "node_glob": "sheep*/rec_sheep*.h5",
        "start": 1_579_171_761_700_000_000,
        "timezone": timezone(timedelta(hours=1), "CET"),
        "duration": int(3608.1 * 1e9),
        "description": (
            "Seven PV are embedded into an outdoor stair in front of a lecture hall. "
            "Frequent foot traffic causes intermittent shadowing. "
            "People are walking normally, no lingering, low to medium traffic. "
            "Sun is low & long shadows of trees move slowly from right to left. "
            "The nodes were powered by a POE Switch and synchronized via a GPS ref-clock."
        ),
        "metadata": {
            "location": "Europe, Germany, Dresden, Helmholtzstraße 18, Barkhausen-Bau",
            "coordinates": "N 51.026467, E 13.723217",
            "energy type": "light",
            "energy source": "natural direct & indirect sun light",
            "transducer": "KXOB25-05X3F-TR (PV, no 100% guarantee)",
            "weather": "Sunny, around 6 degC",
            "weather-source": "https://meteostat.net/de/place/de/dresden?s=10488&t=2020-01-16/2020-01-16",
            # duration & TS are later derived from main data
        },
    },
    "bonito_office_solar": {
        "old_name": "office_new",
        "node_glob": "sheep*/office_sd.h5",
        "start": 1_625_124_518_000_000_000,
        "timezone": timezone(timedelta(hours=2), "CEST"),
        "duration": int(10798.0 * 1e9),
        "description": (
            "Five PV are mounted on doorframes and walls of an office and adjacent hallway. "
            "People enter, leave and operate the lights during the recording. "
            "Lighting is mostly artificial and comes from fluorescent tubes. "
            "The offices have large windows, but the hallway gets almost no natural light. "
            "The nodes were powered by a POE Switch and synchronized via a GPS ref-clock."
        ),
        "metadata": {
            "location": "Europe, Germany, Dresden, Helmholtzstraße 18, Barkhausen-Bau",
            "coordinates": "N 51.026579, E 13.723024",
            "energy type": "light",
            "energy source": "artificial fluorescent light, natural indirect sun light",
            "transducer": "IXYS KX0B25-05X3F (PV)",
            "node0": "room",
            "node1": "room",
            "node2": "room",
            "node3": "hallway",
            "node4": "hallway",
            # duration & TS are later derived from main data
        },
    },
    "bonito_cars_piezo": {
        "old_name": "cars_convoi",
        "node_glob": "sheep*/cars_convoi.h5",
        "start": 1_620_739_600_000_000_000,
        "timezone": timezone(timedelta(hours=2), "CEST"),
        "duration": int(4687.3 * 1e9),
        "description": (
            "Two cars driving convoi over various roads from Windischleuba to Dresden. "
            "Both cars have each 3 piezo transducers in different locations. "
            "One of the cars is an Opel Corsa - probably the following one. "
            "Synchronization and powering of nodes is unknown."
        ),
        "metadata": {
            "location": "Europe, Germany, between Windischleuba & Dresden",
            "coordinates": "N 50.9914555, E 13.0990877",
            "energy type": "kinetic",
            "energy source": "car,motor,road",
            "transducer": "Mide S128-J1FR-1808YB (piezo)",
            "node0": "following car, trunk",
            "node1": "leading car",
            "node2": "leading car",
            "node3": "following car, dashboard",
            "node4": "leading car",
            "node5": "following car, windshield",
            # duration & TS are later derived from main data
        },
    },
    "bonito_washer_piezo": {
        "old_name": "washing_machine",
        "node_glob": "sheep*/washing_machine.h5",
        "start": 1_620_727_713_000_000_000,
        "timezone": timezone(timedelta(hours=2), "CEST"),
        "duration": int(3880.2 * 1e9),
        "description": (
            "Five piezo harvesters are mounted on an industrial washing machine. "
            "The model is called WPB4700H and it runs a 60 degC washing program with maximum load. "
            "All described locations are from POV of looking at the front of the machine. "
            "Transducers move orthogonal to the surface they are put on. "
            "The nodes were powered by a POE Switch and synchronized via a GPS ref-clock."
        ),
        "metadata": {
            "location": "Europe, Germany, Rositz, 295M+PC",
            "coordinates": "N 51.0152002, E 12.3472641",
            "energy type": "kinetic",
            "energy source": "industrial washing machine, WPB4700H",
            "transducer": "Mide S128-J1FR-1808YB (piezo)",
            "node0": "top side - in the middle, slightly moved to front",
            "node1": "back side - top left corner (frontal POV)",
            "node2": "front side - top left corner",
            "node3": "right side - middle of top edge",
            "node4": "front side - in the middle on door",
            "node5": "back side - top right corner (frontal POV)",
            # duration & TS are later derived from main data
        },
    },
    # Add a second version of the washer set as the beginning is rather
    # undynamic. The final 40 minutes which include tumbling are used here.
    "bonito_washer_piezo_tumble_only": {
        "old_name": "washing_machine",
        "node_glob": "sheep*/washing_machine.h5",
        "start": 1_620_729_193_200_000_000,
        "timezone": timezone(timedelta(hours=2), "CEST"),
        "duration": int(2400.0 * 1e9),
        "description": (
            "Five piezo harvesters are mounted on an industrial washing machine. "
            "The model is called WPB4700H and it runs a 60 degC washing program with maximum load. "
            "All described locations are from POV of looking at the front of the machine. "
            "Transducers move orthogonal to the surface they are put on. "
            "The nodes were powered by a POE Switch and synchronized via a GPS ref-clock."
        ),
        "metadata": {
            "location": "Europe, Germany, Rositz, 295M+PC",
            "coordinates": "N 51.0152002, E 12.3472641",
            "energy type": "kinetic",
            "energy source": "industrial washing machine, WPB4700H",
            "transducer": "Mide S128-J1FR-1808YB (piezo)",
            "node0": "top side - in the middle, slightly moved to front",
            "node1": "back side - top left corner (frontal POV)",
            "node2": "front side - top left corner",
            "node3": "right side - middle of top edge",
            "node4": "front side - in the middle on door",
            "node5": "back side - top right corner (frontal POV)",
            # duration & TS are later derived from main data
        },
    },
}


def get_worker_configs(
    path_dir: Path = root_storage_default,
) -> list[tuple[Callable, dict[str, Any]]]:
    """Generate worker-configurations for the conversion of bonito recordings.

    The config is a list of tuples. Each containing a
    callable function and a dict with its arguments.

    Convert bonito environments according to the DATASETS dict.
    """
    cfgs: list[tuple[Callable, dict[str, Any]]] = []
    for new_name, params in DATASETS.items():
        input_dir = path_bonito_input / str(params["old_name"])
        if not input_dir.exists():
            log.error(f"Input-Directory '{input_dir!s}' does not exist -> skipping")
            continue

        files = input_dir.glob(str(params["node_glob"]))

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


def create_meta_data(path_dir: Path = root_storage_default) -> None:
    """Generate a YAML containing the metadata for the dataset.

    Combines data from hdf5-files itself and manually added descriptive data.
    """
    wraps = []
    for new_name, params in DATASETS.items():
        storage_dir = path_dir / "bonito" / new_name
        log.info("Processing %s", storage_dir)
        eprofiles: list[EnergyProfile] = []
        for file_path in storage_dir.glob("*.h5"):
            eprofile = EnergyProfile.derive_from_file(file_path)
            data_update = {
                # pretend data is available on server already (will be copied)
                "data_path": Path("/var/shepherd/content/eenv/nes_lab/")
                / file_path.relative_to(path_dir),
                "data_2_copy": False,
            }
            eprofiles.append(eprofile.model_copy(deep=True, update=data_update))

        if isinstance(params["metadata"], dict):
            timestamp = datetime.fromtimestamp(params["start"] / 1e9, tz=params["timezone"])
            duration = timedelta(seconds=params["duration"] / 1e9)
            params["metadata"]["timestamp"] = timestamp.isoformat(timespec="milliseconds")
            params["metadata"]["duration"] = str(duration)
            log.info(f"{new_name.ljust(30)}\t{timestamp}")

        eenv = EnergyEnvironment(
            name=new_name,
            description=str(params["description"]),
            comment=f"created with {path_file.relative_to(path_file.parents[2])}",
            metadata=params["metadata"],
            # NOTE: intentionally fails if fields are missing
            energy_profiles=eprofiles,
            owner="Ingmar",
            group="NES_Lab",
            visible2group=True,
            visible2all=True,
        )
        wraps.append(
            Wrapper(
                datatype=EnergyEnvironment.__name__,
                parameters=eenv.model_dump(exclude_none=True),
            ).model_dump(exclude_unset=True, exclude_defaults=True)
        )

    wraps_yaml = yaml.safe_dump(
        wraps,
        default_flow_style=False,
        sort_keys=False,
    )
    with (path_dir / "bonito/_metadata_eenvs_bonito.yaml").open("w", encoding="utf-8-sig") as f:
        f.write(wraps_yaml)


if __name__ == "__main__":
    process_mp(get_worker_configs())
    create_meta_data()
