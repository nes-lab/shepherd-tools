"""Client to access a testbed-instance for controlling experiments."""

from .client_fixtures import FixturesClient
from .user_model import User

tb_client = FixturesClient()

__all__ = [
    "tb_client",
    "User",
]
