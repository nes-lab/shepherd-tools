from pathlib import Path

import yaml


def load_yaml(file: str):
    yaml_path = Path(__file__).resolve().with_name(file)
    with open(yaml_path) as _data:
        return yaml.safe_load(_data)
