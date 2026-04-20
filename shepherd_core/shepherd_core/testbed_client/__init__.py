"""Client to access a testbed-instance for controlling experiments."""

from .client_abc import AbcClient
from .client_fixtures import FixturesClient

tb_client: AbcClient = FixturesClient()

__all__ = [
    "tb_client",
]


def set_client(client: AbcClient) -> None:
    global tb_client  # noqa: PLW0603
    tb_client = client


def get_client() -> AbcClient:
    return tb_client
