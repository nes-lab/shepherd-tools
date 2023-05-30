from typing import Optional

from pydantic import conlist
from pydantic import validate_arguments

from ..base.content import NameStr
from ..base.shepherd import ShpModel
from ..experiment.experiment import Experiment
from ..testbed.testbed import Testbed
from .observer_tasks import ObserverTasks


class TestbedTasks(ShpModel):
    """Collection of tasks for all observers included in experiment"""

    name: NameStr
    observer_tasks: conlist(item_type=ObserverTasks, min_items=1, max_items=64)

    @classmethod
    @validate_arguments
    def from_xp(cls, xp: Experiment, tb: Optional[Testbed] = None):
        if tb is None:
            # TODO: just for testing OK
            tb = Testbed(name="shepherd_tud_nes")
        tgt_ids = xp.get_target_ids()
        obs_tasks = [ObserverTasks.from_xp(xp, tb, _id) for _id in tgt_ids]
        return cls(name=xp.name, observer_tasks=obs_tasks)
