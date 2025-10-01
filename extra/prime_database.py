"""Clean models from temporary data (if wanted) & copy to content-dir of core-lib."""

import sys
from pathlib import Path

import yaml
from shepherd_core.data_models import FirmwareDType
from shepherd_core.data_models import ShpModel
from shepherd_core.data_models import Wrapper
from shepherd_core.data_models.content.energy_environment import EnergyEnvironment
from shepherd_core.data_models.content.firmware import Firmware
from shepherd_core.logger import log

from shepherd_core import local_now


def load_model(_model: type(ShpModel), path: Path) -> ShpModel | None:
    """Open and unwrap a shepherd data-model."""
    try:
        return _model.from_file(path)
    except ValueError:
        return None


if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()
    path_db = path_here.parent / "shepherd_core/shepherd_core/data_models/content"
    path_server = Path("/var/shepherd/")
    #  ⤷ can be derived from tb.data_on_server

    if not path_db.exists() or not path_db.is_dir():
        log.error("Path to db must exist and be a directory!")
        sys.exit(1)

    if Path("/var/shepherd/").exists():
        path_content = Path("/var/shepherd/content/")
    else:
        path_content = path_here / "content/"

    if not path_content.exists():
        path_content.mkdir(parents=True)

    files = list(path_content.glob("**/*.yaml"))  # for py>=3.12: case_sensitive=False
    log.debug(" -> got %s YAML-files", len(files))
    fixtures = []

    for file in files:
        model_fw = load_model(Firmware, file)
        model_ee = load_model(EnergyEnvironment, file)

        model = None
        if model_fw is not None:
            data = model_fw.model_dump()
            if isinstance(data["data"], Path):
                data["data"] = data["data"].as_posix()
            path_pos = data["data"].find("/content/")
            path_new = path_server.as_posix() + data["data"][path_pos:]
            data["data"] = path_new
            data["data_type"] = FirmwareDType.path_elf
            data["data_hash"] = None
            data["data_local"] = False
            model = Firmware(**data)
        if model_ee is not None:
            data = model_ee.model_dump()
            path_pos = data["data_path"].as_posix().find("/content/")
            path_new = path_server.as_posix() + data["data_path"].as_posix()[path_pos:]
            data["data_path"] = path_new
            data["data_local"] = False
            model = EnergyEnvironment(**data)

        if model is not None:
            model_dict = model.model_dump()
            model_wrap = Wrapper(
                datatype=type(model).__name__,
                created=local_now(),
                parameters=model_dict,
            )
            fixtures.append(model_wrap.model_dump(exclude_unset=True, exclude_defaults=True))

    model_yaml = yaml.safe_dump(fixtures, default_flow_style=False, sort_keys=False)
    with (path_db / "_external_fixtures.yaml").open("w") as f:
        f.write(model_yaml)
