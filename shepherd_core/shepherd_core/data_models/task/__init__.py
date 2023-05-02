from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import EmailStr
from pydantic import conlist
from pydantic import validate_arguments

from ..base.content import id_int
from ..base.content import name_str
from ..base.content import safe_str
from ..base.shepherd import ShpModel
from ..content.firmware import Firmware
from ..experiment.experiment import Experiment
from ..testbed.target import id_int16
from ..testbed.testbed import Testbed
from .emulation import Compression
from .emulation import EmulationTask
from .programmer import ProgrammerTask

__all__ = [
    # Hierarchical Order
    "TestbedTasks",
    "ObserverTasks",
    "ProgrammerTask",
    "EmulationTask",
    # Enums
    "Compression",
]


class ObserverTasks(ShpModel):
    observer: name_str
    owner_id: id_int

    # PRE PROCESS
    time_prep: datetime
    root_path: Path
    # fw mod & store as hex-file
    fw1: Optional[Firmware]
    fw2: Optional[Firmware]
    fw1_name: safe_str
    fw2_name: safe_str
    custom_id: id_int16

    # actual programming
    prog1: Optional[ProgrammerTask]
    prog2: Optional[ProgrammerTask]

    # MAIN PROCESS
    emulation: Optional[EmulationTask]

    # POST PROCESS
    email: Optional[EmailStr]

    # post_copy, Todo

    @classmethod
    @validate_arguments
    def from_xp(cls, xp: Experiment, tb: Testbed, tgt_id: int):
        if not tb.shared_storage:
            raise ValueError("Implementation currently relies on shared storage!")

        obs = tb.get_observer(tgt_id)
        tgt_cfg = xp.get_target_config(tgt_id)
        xp_dir = "experiment_" + xp.time_start.strftime("%Y-%m-%d_%H:%M:%S")
        fw1_path = tb.data_on_observer / xp_dir / ("fw1_" + obs.name + ".hex")
        fw2_path = tb.data_on_observer / xp_dir / ("fw1_" + obs.name + ".hex")

        return ObserverTasks(
            observer=obs.name,
            owner_id=xp.owner_id,
            time_prep=xp.time_start - tb.prep_duration,
            root_path=tb.data_on_observer / xp_dir,
            fw1=tgt_cfg.firmware1,
            fw2=tgt_cfg.firmware2,
            fw1_name=fw1_path.name,
            fw2_name=fw2_path.name,
            custom_id=tgt_cfg.get_custom_id(tgt_id),
            prog1=ProgrammerTask.from_xp(xp, tb, tgt_id, 1, fw1_path),
            prog2=ProgrammerTask.from_xp(xp, tb, tgt_id, 2, fw2_path),
            emulation=EmulationTask.from_xp(xp, tb, tgt_id),
        )


class TestbedTasks(ShpModel):
    name: name_str
    observer_tasks: conlist(item_type=ObserverTasks, min_items=1, max_items=64)

    @classmethod
    @validate_arguments
    def from_xp(cls, xp: Experiment):
        tb = Testbed(name="shepherd_tud_nes")  # also as argument?
        tgt_ids = xp.get_target_ids()
        obs_tasks = [ObserverTasks.from_xp(xp, tb, _id) for _id in tgt_ids]
        return TestbedTasks(name=xp.name, observer_tasks=obs_tasks)

    def store(self):
        # TODO
        pass
