"""Generator for all artificial Energy-Environments."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from commons import process_mp
from commons import process_sp
from commons import root_storage_default
from ivsurfaces_multivariate_random_walk import get_worker_configs as get_configs_random_walk
from ivtraces_onpattern_random_independent import get_worker_configs as get_configs_onpattern
from ivtraces_onwindow_random_independent import get_worker_configs as get_configs_onwindow
from ivtraces_static import get_worker_configs as get_configs_static


def get_config_for_workers(
    path_dir: Path = root_storage_default,
) -> list[tuple[Callable, dict[str, Any]]]:
    """Generate worker-configurations for all generators.

    The config is a list of tuples. Each containing a
    callable function and a dict with its arguments.
    """
    cfgs: list[tuple[Callable, dict[str, Any]]] = [
        # get_cfgs_random_walk, # see below
        *get_configs_onpattern(path_dir),
        *get_configs_onwindow(path_dir),
        *get_configs_static(path_dir),
    ]
    return cfgs


if __name__ == "__main__":
    process_mp(get_config_for_workers())
    process_sp(get_configs_random_walk())
    # random_walk deliberately set SP as it is MP internally
