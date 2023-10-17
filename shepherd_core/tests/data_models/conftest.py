from pathlib import Path

import yaml


def load_yaml(file: str) -> dict:
    yaml_path = Path(__file__).resolve().with_name(file)
    with yaml_path.open() as _data:
        return yaml.safe_load(_data)


path_fwt = Path(__file__).parent.parent.resolve() / "fw_tools"
names_elf = ["build_msp.elf", "build_nrf.elf"]
files_elf = [path_fwt / name for name in names_elf]
