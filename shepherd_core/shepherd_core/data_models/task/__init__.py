"""Module for task-related data-modules.

These models import externally from all other model-modules!
"""
import pathlib
import pickle
import sys
from pathlib import Path

import yaml

from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.data_models.base.wrapper import Wrapper
from shepherd_core.logger import log

from .emulation import Compression
from .emulation import EmulationTask
from .firmware_mod import FirmwareModTask
from .harvest import HarvestTask
from .observer_tasks import ObserverTasks
from .programming import ProgrammingTask
from .testbed_tasks import TestbedTasks

__all__ = [
    "Compression",
    "EmulationTask",
    "FirmwareModTask",
    "HarvestTask",
    "ObserverTasks",
    "ProgrammingTask",
    "TestbedTasks",
    "extract_tasks",
    "prepare_task",
]


def prepare_task(config: ShpModel | Path | str, observer: str | None = None) -> Wrapper:
    """Open file and extract tasks.

    - Open file (from Path or str of Path)
    - wraps task-model
    - and if it's an TestbedTasks it will extract the correct ObserverTask
    """
    if isinstance(config, str):
        config = Path(config)

    if isinstance(config, Path) and config.exists() and config.suffix.lower() == ".pickle":
        with config.resolve().open("rb") as shp_file:
            try:
                shp_dict = pickle.load(shp_file)  # noqa: S301
            except ModuleNotFoundError as e:
                # NOTE: workaround for interop-problem
                # "No module named 'pathlib._local'; 'pathlib' is not a package"
                log.exception(
                    "Had trouble loading pickled task -> activate pathlib-workaround", exc_info=e
                )
                sys.modules["pathlib._local"] = pathlib
                shp_dict = pickle.load(shp_file)  # noqa: S301
        shp_wrap = Wrapper(**shp_dict)
    elif isinstance(config, Path) and config.exists() and config.suffix.lower() == ".yaml":
        with config.resolve().open() as shp_file:
            shp_dict = yaml.safe_load(shp_file)
        shp_wrap = Wrapper(**shp_dict)
    elif isinstance(config, ShpModel):
        shp_wrap = Wrapper(
            datatype=type(config).__name__,
            parameters=config.model_dump(),
        )
    else:
        msg = f"had unknown input: {type(config)}"
        raise TypeError(msg)

    if shp_wrap.datatype == TestbedTasks.__name__:
        if observer is None:
            log.debug(
                "Task-Set contained TestbedTasks & no observer was provided -> will return TB-Tasks"
            )
            return shp_wrap
        tbt = TestbedTasks(**shp_wrap.parameters)
        log.debug("Loading Testbed-Tasks %s for %s", tbt.name, observer)
        obt = tbt.get_observer_tasks(observer)
        if obt is None:
            msg = f"Observer '{observer}' is not in TestbedTask-Set"
            raise ValueError(msg)
        shp_wrap = Wrapper(
            datatype=type(obt).__name__,
            parameters=obt.model_dump(),
        )
    return shp_wrap


def extract_tasks(shp_wrap: Wrapper, *, no_task_sets: bool = True) -> list[ShpModel]:
    """Make the individual task-sets usable for each observer."""
    if shp_wrap.datatype == ObserverTasks.__name__:
        obt = ObserverTasks(**shp_wrap.parameters)
        content = obt.get_tasks()
    elif shp_wrap.datatype == EmulationTask.__name__:
        content = [EmulationTask(**shp_wrap.parameters)]
    elif shp_wrap.datatype == HarvestTask.__name__:
        content = [HarvestTask(**shp_wrap.parameters)]
    elif shp_wrap.datatype == FirmwareModTask.__name__:
        content = [FirmwareModTask(**shp_wrap.parameters)]
    elif shp_wrap.datatype == ProgrammingTask.__name__:
        content = [ProgrammingTask(**shp_wrap.parameters)]
    elif shp_wrap.datatype == TestbedTasks.__name__:
        if no_task_sets:
            raise ValueError("Model in Wrapper was TestbedTasks -> Task-Sets not allowed!")
        content = [TestbedTasks(**shp_wrap.parameters)]
    else:
        msg = f"Extractor had unknown task: {shp_wrap.datatype}"
        raise ValueError(msg)

    return content
