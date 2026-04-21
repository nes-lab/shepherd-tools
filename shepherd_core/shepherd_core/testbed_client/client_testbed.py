"""Client-Class to access a testbed instance over the web."""

from typing import Any

from shepherd_core.config import core_config

from .client_abc import AbcClient


class TestbedClient(AbcClient):
    """Client-Class to access a testbed instance over the web.

    For online-queries the lib can be connected to a testbed-server.
    """

    def __init__(self, server: str | None = None) -> None:
        """Connect to Testbed-Server with optional token and server-address.

        server: optional address to shepherd-server-endpoint
        token: your account validation. if omitted, only public data is available
        """
        super().__init__()
        # add default values
        self._server: str = str(core_config.TESTBED_SERVER) if server is None else server

    # ABC Functions below

    def list_resource_types(self) -> list[str]:
        raise NotImplementedError("TODO")

    def list_resource_ids(self, model_type: str) -> list[int]:
        raise NotImplementedError("TODO")

    def list_resource_names(self, model_type: str) -> list[str]:
        raise NotImplementedError("TODO")

    def get_resource_item(
        self, model_type: str, uid: int | None = None, name: str | None = None
    ) -> dict:
        raise NotImplementedError("TODO")

    def _try_inheritance(
        self, model_type: str, values: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        raise NotImplementedError("TODO")
