"""Generator for all synthetic Energy-Environments."""

from collections.abc import Callable
from typing import Any

from commons import process_mp
from commons import process_sp
from ivsurfaces_multivariate_random_walk import create_meta_data as meta_random_walk
from ivsurfaces_multivariate_random_walk import get_worker_configs as get_configs_random_walk
from ivtraces_on_off_markov import create_meta_data as meta_onpattern
from ivtraces_on_off_markov import get_worker_configs as get_configs_onpattern
from ivtraces_on_off_windows import create_meta_data as meta_onwindow
from ivtraces_on_off_windows import get_worker_configs as get_configs_onwindow
from ivtraces_static import create_meta_data as meta_static
from ivtraces_static import get_worker_configs as get_configs_static


def get_config_for_workers() -> list[tuple[Callable, dict[str, Any]]]:
    """Generate worker-configurations for all generators.

    The config is a list of tuples. Each containing a
    callable function and a dict with its arguments.
    """
    cfgs: list[tuple[Callable, dict[str, Any]]] = [
        # get_cfgs_random_walk, # see below
        *get_configs_static(),
        *get_configs_onwindow(),
        *get_configs_onpattern(),
    ]
    return cfgs


def create_meta_data() -> None:
    """Generate a YAML containing the metadata for the dataset.

    Combines data from hdf5-files itself and manually added descriptive data.
    """
    process_mp(
        worker_cfgs=[
            (meta_static, {}),
            (meta_onwindow, {}),
            (meta_onpattern, {}),
            (meta_random_walk, {}),
        ]
    )


if __name__ == "__main__":
    process_mp(get_config_for_workers())
    process_sp(get_configs_random_walk())
    # random_walk deliberately set SP as it is MP internally
    create_meta_data()
