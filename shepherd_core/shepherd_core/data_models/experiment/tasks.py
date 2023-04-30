from pydantic import conlist

from ..base.content import name_str
from ..base.shepherd import ShpModel
from ..testbed.testbed import Testbed
from .emulation_config import EmulationConfig
from .experiment import Experiment
from .programmer_config import ProgrammerConfig


class ObserverTasks(ShpModel):
    observer: name_str

    # pre_copy

    programmer: ProgrammerConfig

    emulation: EmulationConfig

    # post_copy

    @classmethod
    def from_xp(cls, xp: Experiment, tb: Testbed, tgt_id: int):
        obs = tb.get_observer(tgt_id)
        tgt_cfg = xp.get_target_config(tgt_id)
        elem = {}

        return ObserverTasks(**elem)


class TestbedTasks(ShpModel):
    tasks: conlist(item_type=ObserverTasks, min_items=1, max_items=64)

    @classmethod
    def from_xp(cls, xp: Experiment):
        tb = Testbed(name="shepherd_tud_nes")  # also as argument?
        obs_tasks = []
        tgt_ids = xp.get_target_ids()
        for _id in tgt_ids:
            task = ObserverTasks.from_xp(xp, tb, _id)
            obs_tasks.append(task)
        return TestbedTasks(tasks=obs_tasks)
