"""Client to access a testbed-instance for controlling experiments."""

from .client_abc import AbcClient
from .client_fixtures import FixturesClient

tb_client: AbcClient = FixturesClient()

__all__ = [
    "tb_client",
]
