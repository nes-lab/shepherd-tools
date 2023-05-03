from pydantic import conlist
from pydantic import validate_arguments

from ..base.content import name_str
from ..base.shepherd import ShpModel
from ..experiment.experiment import Experiment
from ..testbed.testbed import Testbed
from .observer_tasks import ObserverTasks


class TestbedTasks(ShpModel):
    """Collection of tasks for all observers included in experiment"""

    name: name_str
    observer_tasks: conlist(item_type=ObserverTasks, min_items=1, max_items=64)

    @classmethod
    @validate_arguments
    def from_xp(cls, xp: Experiment):
        tb = Testbed(name="shepherd_tud_nes")  # also as argument?
        tgt_ids = xp.get_target_ids()
        obs_tasks = [ObserverTasks.from_xp(xp, tb, _id) for _id in tgt_ids]
        return cls(name=xp.name, observer_tasks=obs_tasks)
