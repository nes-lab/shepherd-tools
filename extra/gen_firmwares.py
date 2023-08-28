"""
script will:
- download and extract firmwares from https://github.com/orgua/shepherd-targets/releases
- generate embedded firmware-models
- it assumes sub-dirs in the same dir with ./build.elf in it
"""
import os
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import yaml

from shepherd_core.data_models.content.firmware import Firmware
from shepherd_core.logger import logger

if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()

    # config
    link = "https://github.com/orgua/shepherd-targets/releases/latest/download/firmwares.zip"
    # ⤷ already includes embedded-firmware-models
    path_meta = path_here / "content" / "metadata_fw.yaml"

    data = urlopen(link).read()  # noqa: S310
    with ZipFile(BytesIO(data), "r") as zip_ref:
        zip_ref.extractall(path_here)

    if not path_meta.exists():
        logger.error("Metadata-file not found, will stop (%s)", path_meta.as_posix())
    else:
        with open(path_meta) as file_meta:
            metadata = yaml.safe_load(file_meta)["metadata"]

        for _fw, _descr in metadata.items():
            path_fw = path_here / "content" / _fw
            files_elf = [each for each in os.listdir(path_fw) if each.endswith(".elf")]

            if len(files_elf) > 1:
                logger.warning(
                    "More than one .ELF in directory -> will use first of %s", files_elf
                )
            path_elf = path_fw / files_elf[0]

            if path_elf.exists():
                Firmware.from_firmware(
                    file=path_elf,
                    name=_fw,
                    description=_descr,
                    owner="Ingmar",
                    group="NES Lab",
                    visible2group=True,
                    visible2all=True,
                ).to_file(path_elf.with_suffix(".yaml"))
            else:
                logger.error("FW not found, will skip: %s", path_elf.as_posix())
