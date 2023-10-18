from typing import List
from typing import Optional

from pydantic import EmailStr
from pydantic import Field
from pydantic import validate_call
from typing_extensions import Annotated
from typing_extensions import Self

from ..base.content import NameStr
from ..base.shepherd import ShpModel
from ..experiment.experiment import Experiment
from ..testbed.testbed import Testbed
from .observer_tasks import ObserverTasks


class TestbedTasks(ShpModel):
    """Collection of tasks for all observers included in experiment"""

    name: NameStr
    observer_tasks: Annotated[List[ObserverTasks], Field(min_length=1, max_length=128)]

    # POST PROCESS
    email: Optional[EmailStr] = None

    @classmethod
    @validate_call
    def from_xp(cls, xp: Experiment, tb: Optional[Testbed] = None) -> Self:
        if tb is None:
            # TODO: just for testing OK
            tb = Testbed(name="shepherd_tud_nes")
        tgt_ids = xp.get_target_ids()
        obs_tasks = [ObserverTasks.from_xp(xp, tb, _id) for _id in tgt_ids]
        return cls(
            name=xp.name,
            observer_tasks=obs_tasks,
            email=xp.email_results,
        )

    def get_observer_tasks(self, observer: str) -> Optional[ObserverTasks]:
        for tasks in self.observer_tasks:
            if observer == tasks.observer:
                return tasks
        return None

    def get_output_paths(self) -> dict:
        # TODO: computed field preferred, but they don't work here, as
        #  - they are always stored in yaml despite "repr=False"
        #  - solution will shift to some kind of "result"-datatype that is combinable
        values = {}
        for obt in self.observer_tasks:
            values = {**values, **obt.get_output_paths()}
        return values
