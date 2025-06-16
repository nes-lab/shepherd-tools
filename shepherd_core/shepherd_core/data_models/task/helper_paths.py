from pathlib import Path


def path_posix(path: Path) -> Path:
    return Path(path.as_posix().replace("\\", "/"))