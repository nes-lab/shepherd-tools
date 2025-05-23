"""
Goals:
- add structured metadata
- allow relative pathing - with real inputs (full Path() to rel)
- allow list of paths, or even dict, but still slice[:] operation
"""
from pathlib import PurePosixPath, Path
from typing import Annotated, Mapping
from pydantic import Field
from shepherd_core.data_models import ContentModel, ShpModel


# TODO: should dtype, duration, energy_Ws be kept with the path?
#       So we would have to create a scalar energy profile
# TODO: add typecast from WindowPath / PosixPath -> Pure ... pydantic does not support it automatically

class EEnv2(ContentModel):

    metadata: Mapping[str, str] = {}

    #data_path: PurePosixPath
    data_paths: Annotated[list[PurePosixPath], Field(min_length=1, max_length=128)]
    repetitions_ok: bool = False

    def __getitem__(self, value):
        if isinstance(value, slice):
            print(str(value))
        if isinstance(value, int):
            print(str(value))

    def __len__(self) -> int:
        return len(self.data_paths)

class TargetConfig2(ShpModel):

    target_IDs: Annotated[list[int], Field(min_length=1, max_length=128)]
    eenvs: list[EEnv2]


if __name__ == "__main__":

    eenv = EEnv2(
        data_paths=[Path(".nagut"), Path("/pagut"), PurePosixPath("spaghetti")],
        repetitions_ok=True,
    )

    slice1 = eenv[2]
    slice2 = eenv[5]
    slice3 = eenv[1:]

    print("done")
