from pathlib import Path
from typing import Optional

from .base.calibration import CalibrationCape
from .base.calibration import CalibrationEmulator
from .base.calibration import CalibrationHarvester
from .base.calibration import CalibrationPair
from .base.calibration import CalibrationSeries
from .base.content import ContentModel
from .base.fixture import Fixtures
from .base.shepherd import ShpModel
from .base.wrapper import Wrapper
from .content.energy_environment import EnergyDType
from .content.energy_environment import EnergyEnvironment
from .content.firmware import Firmware
from .content.firmware import FirmwareDType
from .content.virtual_harvester import VirtualHarvesterConfig
from .content.virtual_source import VirtualSourceConfig
from .experiment.experiment import Experiment
from .experiment.observer_features import GpioActuation
from .experiment.observer_features import GpioEvent
from .experiment.observer_features import GpioLevel
from .experiment.observer_features import GpioTracing
from .experiment.observer_features import PowerTracing
from .experiment.observer_features import SystemLogging
from .experiment.target_config import TargetConfig

__all__ = [
    # Core
    "CalibrationCape",
    "CalibrationEmulator",
    "CalibrationHarvester",
    "CalibrationSeries",
    "CalibrationPair",
    "ContentModel",
    "ShpModel",
    "Fixtures",
    "Wrapper",
    # User Content
    "Experiment",
    "TargetConfig",
    "Firmware",
    "FirmwareDType",
    "SystemLogging",
    "PowerTracing",
    "GpioTracing",
    "GpioActuation",
    "GpioEvent",
    "GpioLevel",
    "EnergyEnvironment",
    "EnergyDType",
    "VirtualSourceConfig",
    "VirtualHarvesterConfig",
    # test-container & placeholder
    "fixtures",
]


class FixtureSet:
    def __init__(self):
        self.path = Path(__file__) / "fixtures"

    def load(self, path: Optional[Path] = None) -> None:
        if path:
            self.path = path


fixtures = FixtureSet()
