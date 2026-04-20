"""Client to access a testbed-instance for controlling experiments."""

from .client_abc import Client
from .client_fixtures import FixturesClient

tb_client: Client = FixturesClient()

__all__ = [
    "tb_client",
]


def set_client(client: Client) -> None:
    global tb_client  # noqa: PLW0603
    tb_client = client


def get_client() -> Client:
    return tb_client
