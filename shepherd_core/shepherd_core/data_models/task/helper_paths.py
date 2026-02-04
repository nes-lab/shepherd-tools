r"""Helper FN to avoid unwanted behavior.

On WinOS Path("\xyz") gets transformed to "/xyz", but not on linux.
When sending an experiment via fastapi, this bug gets triggered.
"""

from pathlib import Path


def path_posix(path: Path) -> Path:
    r"""Help Linux to get from "\xyz" to "/xyz".

    This isn't a problem on WinOS and gets triggered when sending experiments via fastapi.
    """
    return Path(path.as_posix().replace("\\", "/"))
