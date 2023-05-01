from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import EmailStr
from pydantic import conlist

from ..base.content import id_str
from ..base.content import name_str
from ..base.content import safe_str
from ..base.shepherd import ShpModel
from ..content.firmware import Firmware
from ..experiment.experiment import Experiment
from ..testbed.target import id_int
from ..testbed.testbed import Testbed
from .emulation import Compression
from .emulation import EmulationTask
from .programmer import ProgrammerTask

__all__ = [
    "TestbedTasks",
    "ObserverTasks",
    "EmulationTask",
    "ProgrammerTask",
    # Enums
    "Compression",
]


class ObserverTasks(ShpModel):
    observer: name_str
    owner_id: id_str

    # PRE PROCESS
    pre_start: datetime
    root_path: Path
    # fw mod & store as hex-file
    fw1: Optional[Firmware]
    fw2: Optional[Firmware]
    fw1_name: safe_str
    fw2_name: safe_str
    custom_id: id_int
    # actual programming
    prog1: Optional[ProgrammerTask]
    prog1: Optional[ProgrammerTask]

    # MAIN PROCESS
    emulation: Optional[EmulationTask]

    # POST PROCESS
    email: Optional[EmailStr]

    # post_copy, Todo

    @classmethod
    def from_xp(cls, xp: Experiment, tb: Testbed, tgt_id: int):
        if not tb.shared_storage:
            raise ValueError("Implementation currently relies on shared storage!")

        observer = tb.get_observer(tgt_id)
        tgt_cfg = xp.get_target_config(tgt_id)
        directory = "experiment_" + xp.time_start.strftime("%Y-%m-%d_%H:%M:%S")
        return ObserverTasks(
            observer=observer.name,
            owner_id=xp.owner_id,
            pre_start=xp.time_start - tb.pre_duration,
            root_path=tb.data_on_observer / directory,
            fw1=tgt_cfg.firmware1,
            fw2=tgt_cfg.firmware2,
            fw1_name="fw1_" + observer + ".hex",
            fw2_name="fw2_" + observer + ".hex",
            custom_id=tgt_cfg.get_custom_id(tgt_id),
            prog1=ProgrammerTask.from_xp(xp, tgt_cfg, 1),
            prog2=ProgrammerTask.from_xp(xp, tgt_cfg, 2),
            emulation=EmulationTask.from_xp(xp),
        )


class TestbedTasks(ShpModel):
    tasks: conlist(item_type=ObserverTasks, min_items=1, max_items=64)

    @classmethod
    def from_xp(cls, xp: Experiment):
        tb = Testbed(name="shepherd_tud_nes")  # also as argument?
        tgt_ids = xp.get_target_ids()
        obs_tasks = [ObserverTasks.from_xp(xp, tb, _id) for _id in tgt_ids]
        return TestbedTasks(tasks=obs_tasks)

    def store(self):
        # TODO
        pass
