r"""Helper FN to avoid unwanted behavior.

On windows Path("\xyz") gets transformed to "/xyz", but not on linux.
When sending an experiment via fastapi, this bug gets triggered.
"""

from pathlib import Path


def path_posix(path: Path) -> Path:
    r"""Help Linux to get from "\xyz" to "/xyz".

    This isn't a problem on windows and gets triggered when sending XP via fastapi.
    """
    return Path(path.as_posix().replace("\\", "/"))
