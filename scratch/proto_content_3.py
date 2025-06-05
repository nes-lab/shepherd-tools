import yaml
import shutil
from copy import deepcopy
from collections.abc import Iterable
from enum import Enum
from pathlib import Path
from typing import Any, Optional, List, Annotated, Tuple
from typing_extensions import Self

from pydantic import PositiveFloat, model_validator, BaseModel, Field

from shepherd_core import logger
from shepherd_core.data_models import ShpModel
from shepherd_core.data_models.base.content import IdInt
from shepherd_core.data_models.content.virtual_source import VirtualSourceConfig
from shepherd_core.data_models.testbed.target import IdInt16, Target
from shepherd_core.data_models.experiment.observer_features import GpioActuation, GpioTracing, PowerTracing, UartLogging

class Firmware(ShpModel):
    name: str

class EnergyEnvironment(ShpModel):
    name: str
    # TODO this would be part of ContentModel

    data_paths: List[Path]
    #⤷  list of data files corresponding to the nodes

    duration: PositiveFloat
    #⤷  in s; duration of the recorded environment (of all profiles)

    metadata: Optional[dict] = None
    #⤷  information about the environment as a dict
    # typical keys: recording-tool/generation-script, maximum harvestable energy, location (address/GPS), site-description (building/forest),
    #    weather, nodes (for each node: transducer, location within experiment, datatype - surface/trace, max-harvestable-energy)

    def export(self, output_path: Path):
        output_path.mkdir(exist_ok=False)

        # Copy data files

        for (i, profile) in enumerate(self.profiles):
            # Number the sheep to avoid collisions. Preserve extensions
            relative_path = [f'sheep{i}{profile.data_path.suffix}' for profile in self.profiles]
            shutil.copy(profile.data_path, output_path / relative_path)

        # Create information file

        content = self.model_dump()
        # Use relative paths now
        for (i, path) in relative_paths:
            content['profiles'][i]['data_path'] = path

        with open('eenv.yaml', 'w') as file:
            yaml.dump(content, file, default_flow_style=False)

    @model_validator(mode="before")
    @classmethod
    def cast_path(cls, values: dict[str, Any]) -> dict[str, Any]:
        if "data_paths" in values and isinstance(values["data_paths"], Iterable):
            values["data_paths"] = [path.absolute() for path in values["data_paths"]]
        return values


class TargetConfig(ShpModel):
    target_ID: int
    custom_ID: Optional[int] = None

    energy_profile: tuple[str, int]

    """ input for the virtual source """
    virtual_source: Optional[VirtualSourceConfig] = None # TODO made this none for testing

    target_delays: Optional[
        Annotated[list[Annotated[int, Field(ge=0)]], Field(min_length=1, max_length=128)]
    ] = None
    """ ⤷ individual starting times

    - allows to use the same environment
    - not implemented ATM
    """

    # TODO made this optional for demo
    firmware1: Optional[Firmware]
    """ ⤷ omitted FW gets set to neutral deep-sleep"""
    firmware2: Optional[Firmware] = None
    """ ⤷ omitted FW gets set to neutral deep-sleep"""

    power_tracing: Optional[PowerTracing] = None
    gpio_tracing: Optional[GpioTracing] = None
    gpio_actuation: Optional[GpioActuation] = None
    uart_logging: Optional[UartLogging] = None

class Experiment(ShpModel, title="Config of an Experiment"):
    """Config for experiments on the testbed emulating energy environments for target nodes."""
    # targets
    target_configs: Annotated[list[TargetConfig], Field(min_length=1, max_length=128)]

class TargetConfigBuilder:
    def __init__(self, target_IDs):
        self.target_IDs = target_IDs
        self.firmwares = [None for i in target_IDs]
        self.eenvs = [None for i in target_IDs]

    def with_firmware(self, firmware, target_IDs=None):
        if target_IDs == None:
            target_IDs = self.target_IDs
        for i in range(len(self.target_IDs)):
            if self.target_IDs[i] in target_IDs:
                self.firmwares[i] = firmware
        return self

    def with_eenv(self, eenv, mapping=None):
        if mapping is None:
            mapping = {id: i for (i, id) in enumerate(self.target_IDs)}

        for (i, id) in enumerate(self.target_IDs):
            if id in mapping:
                self.eenvs[i] = (eenv.name, mapping[id])

        return self

    def build(self):
        return [TargetConfig(target_ID=self.target_IDs[i],
                             firmware1=self.firmwares[i],
                             energy_profile=self.eenvs[i]) for i in range(len(self.target_IDs))]

if __name__ == "__main__":
    from pprint import pprint
    # Dummy firmware
    dummy_fw = Firmware(name='Dummy Firmware')
    dummy_fw_2 = Firmware(name='Another Firmware')

    # Dummy eenv (this would correspond to an eenv from the server)
    path1 = Path('./shp1.h5')
    path2 = Path('./shp2.h5')
    path3 = Path('./shp3.h5')
    path4 = Path('./shp4.h5')
    dummy_eenv = EnergyEnvironment(name='Dummy Experiment', data_paths=[path1, path2], duration=3600, metadata={ })
    # Imagine this is a different energy environment
    dummy_eenv_2 = EnergyEnvironment(name='Another Experiment', data_paths=[path1, path2], duration=3600, metadata={ })

    print(f'Minimal Configuration:')
    cfgs = (TargetConfigBuilder(target_IDs=range(10, 14))
           .with_firmware(dummy_fw)
           .with_eenv(dummy_eenv)
           .build())
    pprint(Experiment(target_configs=cfgs).model_dump())
    print('---\n\n')

    print(f'Mixed Environments:')
    cfgs_2 = (TargetConfigBuilder(target_IDs=range(10, 15))
              .with_firmware(dummy_fw)
              .with_eenv(dummy_eenv, mapping={10: 1, 11: 2, 12: 3})
              .with_eenv(dummy_eenv_2, mapping={13: 0, 14: 1})
              .build())
    pprint(Experiment(target_configs=cfgs_2).model_dump())
    print('---\n\n')

    print(f'Complex/Manual Configuration:')
    cfgs_3 = target_configs=[
        TargetConfig(target_ID=4, firmware1=dummy_fw, energy_profile=(dummy_eenv.name, 0)),
        TargetConfig(target_ID=7, firmware1=dummy_fw_2, energy_profile=(dummy_eenv.name, 0)),
        TargetConfig(target_ID=13, firmware1=dummy_fw, energy_profile=(dummy_eenv.name, 7)),
        TargetConfig(target_ID=22, firmware1=dummy_fw, energy_profile=(dummy_eenv.name, 3))
    ]
    pprint(Experiment(target_configs=cfgs_3).model_dump())
    print('---\n\n')
