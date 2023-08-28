"""
script will:
- clean Models from temporary data
- copy models to content-dir of core-lib
"""
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from shepherd_core.data_models import FirmwareDType
from shepherd_core.data_models import Wrapper
from shepherd_core.data_models.content.energy_environment import EnergyEnvironment
from shepherd_core.data_models.content.firmware import Firmware
from shepherd_core.logger import logger
from shepherd_core.testbed_client.fixtures import get_files


def get_fw(path: Path) -> Optional[Firmware]:
    try:
        return Firmware.from_file(path)
    except ValueError:
        return None


def get_eenv(path: Path) -> Optional[EnergyEnvironment]:
    try:
        return EnergyEnvironment.from_file(path)
    except ValueError:
        return None


if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()
    path_db = (
        path_here.parent / "shepherd_core" / "shepherd_core" / "data_models" / "content"
    )

    if not path_db.exists() or not path_db.is_dir():
        logger.error("Path to db must exist and be a directory!")
        exit(1)

    files = get_files(path_here / "content", ".yaml")
    fixtures = []

    for file in files:
        model_fw = get_fw(file)
        model_ee = get_eenv(file)

        model = None
        if model_fw is not None:
            data = model_fw.model_dump()
            data["data"] = "generic_path.elf"
            data["data_type"] = FirmwareDType.path_elf
            data["data_hash"] = None
            model = Firmware(**data)
        if model_ee is not None:
            data = model_ee.model_dump()
            data["data_path"] = "generic_path.h5"
            model = EnergyEnvironment(**data)

        if model is not None:
            model_dict = model.model_dump()
            model_wrap = Wrapper(
                datatype=type(model).__name__,
                created=datetime.now(),
                parameters=model_dict,
            )
            fixtures.append(
                model_wrap.model_dump(exclude_unset=True, exclude_defaults=True)
            )

    model_yaml = yaml.safe_dump(fixtures, default_flow_style=False, sort_keys=False)
    with open(path_db / "_external_fixtures.yaml", "w") as f:
        f.write(model_yaml)
