"""Pre-init complex types for improved perf."""

from .virtual_harvester_config import VirtualHarvesterConfig

#  TODO: is documentation still fine?
vhrv_mppt_opt = VirtualHarvesterConfig(name="mppt_opt")
