"""Collection of tasks for all observers included in experiment."""

from collections.abc import Iterable
from pathlib import Path
from pathlib import PurePosixPath
from typing import Annotated
from typing import final

from pydantic import Field
from pydantic import validate_call
from typing_extensions import Self

from shepherd_core.config import config
from shepherd_core.data_models.base.content import NameStr
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.data_models.experiment.experiment import Experiment
from shepherd_core.data_models.testbed.testbed import Testbed

from .observer_tasks import ObserverTasks


@final
class TestbedTasks(ShpModel):
    """Collection of tasks for all observers included in experiment."""

    name: NameStr
    observer_tasks: Annotated[list[ObserverTasks], Field(min_length=1, max_length=128)]

    @classmethod
    @validate_call
    def from_xp(cls, xp: Experiment, tb: Testbed | None = None) -> Self:
        if tb is None:
            # TODO: is tb-argument really needed? prob. not
            tb = Testbed()  # this will query the first (and only) entry of client

        tgt_ids = xp.get_target_ids()
        xp_folder = xp.folder_name()
        obs_tasks = [ObserverTasks.from_xp(xp, xp_folder, tb, id_) for id_ in tgt_ids]
        return cls(
            name=xp.name,
            observer_tasks=obs_tasks,
        )

    def get_observer_tasks(self, observer: str) -> ObserverTasks | None:
        for tasks in self.observer_tasks:
            if observer == tasks.observer:
                return tasks
        return None

    def get_observers(self) -> set[str]:
        return {tasks.observer for tasks in self.observer_tasks}

    def get_output_paths(self) -> dict[str, Path]:
        # TODO: computed field preferred, but they don't work here, as
        #  - they are always stored in yaml despite "repr=False"
        #  - solution will shift to some kind of "result"-datatype that is combinable
        values: dict[str, Path] = {}
        for obt in self.observer_tasks:
            values = {**values, **obt.get_output_paths()}
        return values

    def is_contained(self, paths: Iterable[PurePosixPath] = config.PATHS_ALLOWED) -> bool:
        """Limit paths to allowed directories.

        This is the central checking point for the webserver.
        """
        return all(obt.is_contained(paths) for obt in self.observer_tasks)
