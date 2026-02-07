"""Collection of tasks for selected observer included in experiment."""

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from pathlib import PurePosixPath
from typing import Annotated
from typing import final

from pydantic import validate_call
from typing_extensions import Self
from typing_extensions import deprecated

from shepherd_core.data_models.base.content import IdInt
from shepherd_core.data_models.base.content import NameStr
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.data_models.experiment.experiment import Experiment
from shepherd_core.data_models.testbed.testbed import Testbed

from .emulation import EmulationTask
from .firmware_mod import FirmwareModTask
from .helper_paths import path_posix
from .programming import ProgrammingTask


@final
class ObserverTasks(ShpModel):
    """Collection of tasks for selected observer included in experiment."""

    observer: NameStr

    # PRE PROCESS
    time_prep: datetime | None = None  # TODO: currently not used
    root_path: Path

    # fw mod, store as hex-file and program
    fw1_mod: FirmwareModTask | None = None
    fw2_mod: FirmwareModTask | None = None
    fw1_prog: ProgrammingTask | None = None
    fw2_prog: ProgrammingTask | None = None

    # MAIN PROCESS
    emulation: EmulationTask | None = None

    # deprecations, TODO: remove before public release
    owner_id: Annotated[IdInt | None, deprecated("not needed anymore")] = None
    abort_on_error: Annotated[bool, deprecated("has no effect")] = False

    # post_copy / cleanup, Todo: could also just intake emuTask
    #  - delete firmwares
    #  - decode uart
    #  - downsample
    #  - zip it

    @classmethod
    @validate_call
    def from_xp(cls, xp: Experiment, xp_folder: str | None, tb: Testbed, tgt_id: IdInt) -> Self:
        if not tb.shared_storage:
            raise ValueError("Implementation currently relies on shared storage!")

        obs = tb.get_observer(tgt_id)
        if xp_folder is None:
            xp_folder = xp.folder_name()  # moved a layer up for consistent naming
        root_path = tb.data_on_observer / "experiments" / xp_folder
        fw_paths = [root_path / f"fw{i_}_{obs.name}.hex" for i_ in [1, 2]]

        return cls(
            observer=obs.name,
            # time_prep=
            root_path=path_posix(root_path),
            fw1_mod=FirmwareModTask.from_xp(xp, tb, tgt_id, 1, fw_paths[0]),
            fw2_mod=FirmwareModTask.from_xp(xp, tb, tgt_id, 2, fw_paths[1]),
            fw1_prog=ProgrammingTask.from_xp(xp, tb, tgt_id, 1, fw_paths[0]),
            fw2_prog=ProgrammingTask.from_xp(xp, tb, tgt_id, 2, fw_paths[1]),
            emulation=EmulationTask.from_xp(xp, tb, tgt_id, root_path),
        )

    def get_tasks(self) -> list[ShpModel]:
        task_names = ["fw1_mod", "fw2_mod", "fw1_prog", "fw2_prog", "emulation"]
        tasks = []

        for task_name in task_names:
            if not hasattr(self, task_name):
                continue
            task = getattr(self, task_name)
            if task is None:
                continue
            tasks.append(task)
        return tasks

    def get_output_paths(self) -> dict[str, Path]:
        values: dict[str, Path] = {}
        if isinstance(self.emulation, EmulationTask):
            if self.emulation.output_path is None:
                raise ValueError("Emu-Task should have a valid output-path")
            values[self.observer] = self.emulation.output_path
        return values

    def is_contained(self, paths: Iterable[PurePosixPath]) -> bool:
        """Limit paths to allowed directories."""
        all_ok = any(PurePosixPath(self.root_path).is_relative_to(path) for path in paths)
        all_ok &= self.fw1_mod is None or self.fw1_mod.is_contained(paths)
        all_ok &= self.fw2_mod is None or self.fw2_mod.is_contained(paths)
        all_ok &= self.fw1_prog is None or self.fw1_prog.is_contained(paths)
        all_ok &= self.fw2_prog is None or self.fw2_prog.is_contained(paths)
        all_ok &= self.emulation is None or self.emulation.is_contained(paths)
        return all_ok
