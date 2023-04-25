import copy
from pathlib import Path
from typing import Optional

import yaml

from shepherd_core import logger

# Proposed field-name:
# - inheritance
# - inherit_from
# - inheritor
# - hereditary
# - based_on


class Fixtures:
    def __init__(self, file_path: Path, model_name: str):
        # TODO: input could be just __file__(str)
        self.path: Path = file_path
        self.name: str = model_name
        self.elements: dict = {}
        with open(self.path) as fix_data:
            fixtures = yaml.safe_load(fix_data)
            for fixture in fixtures:
                if not isinstance(fixture, dict):
                    continue
                if "fields" not in fixture or "model" not in fixture:
                    continue
                if fixture["model"].lower() != model_name.lower():
                    continue
                if "name" not in fixture["fields"]:
                    continue
                name = str(fixture["fields"]["name"]).lower()
                data = fixture["fields"]
                self.elements[name] = data

    def __getitem__(self, key) -> dict:
        key = key.lower()
        if key in self.elements:
            return self.elements[key]
        else:
            raise ValueError(f"{self.name} '{key}' not found!")

    def keys(self):  # -> _dict_keys[Any, Any]:
        return self.elements.keys()

    def inheritance(self, values: dict, chain: Optional[list] = None) -> (dict, list):
        if chain is None:
            chain = []
        values = copy.copy(values)
        if "inherit_from" in values:
            fixture_name = values.pop(
                "inherit_from",
            )
            # ⤷ will also remove entry from dict
            if "name" in values and len(chain) < 1:
                base_name = values.get("name")
                if base_name in chain:
                    raise ValueError(
                        f"Inheritance-Circle detected ({base_name} already in {chain})",
                    )
                if base_name == fixture_name:
                    raise ValueError(
                        f"Inheritance-Circle detected ({base_name} == {fixture_name})",
                    )
                chain.append(base_name)
            fixture_base = copy.copy(self[fixture_name])
            logger.debug("'%s' will inherit from '%s'", self.name, fixture_name)
            fixture_base["name"] = fixture_name
            chain.append(fixture_name)
            base_dict, chain = self.inheritance(values=fixture_base, chain=chain)
            for key, value in values.items():
                base_dict[key] = value
            values = base_dict

        elif "name" in values and values.get("name").lower() in self.elements:
            fixture_name = values.get("name").lower()
            fixture_base = copy.copy(self[fixture_name])
            fixture_base["name"] = fixture_name
            if "inherit_from" in fixture_base:
                # as long as this key is present this will act recursively
                chain.append(fixture_name)
                values, chain = self.inheritance(values=fixture_base, chain=chain)
            else:
                values = fixture_base

        return values, chain  # TODO: add _chain to values
