"""Client-Class to access the file based fixtures.

Fixtures == OffLineDemoInstances
offline:	core  - fixtClient
webDev:	    core  - webClient  <->	webSrv - fixtClient
webUser:	core  - webClient  <->  webSrv - DbClient
webInfra:   core  - webClient+ <->  webSrv - DbClient

Users, Sheep and ServerApps should have access to the same DB via WebClient

Note: ABC and FixClient can't be in separate files when tb_client should
      default to FixClient (circular import)

TODO: Comfort functions missing
    - fixtures to DB, and vice versa
"""

from typing import Any
from typing import final

from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.data_models.base.wrapper import Wrapper
from shepherd_core.logger import log

from .client_abc import Client
from .fixtures import Fixtures


@final
class FixturesClient(Client):
    """Client-Class to access the file based fixtures."""

    def __init__(self) -> None:
        super().__init__()
        self.fixture_cache: Fixtures = Fixtures()

    def insert_content(self, data: ShpModel) -> bool:
        wrap = Wrapper(
            datatype=type(data).__name__,
            parameters=data.model_dump(),
        )
        self.fixture_cache.insert_model(wrap)
        return True

    def list_content_types(self) -> list[str]:
        return list(self.fixture_cache.components)

    def list_content_ids(self, model_type: str) -> list[int]:
        return list(self.fixture_cache[model_type].elements_by_id.keys())

    def list_content_names(self, model_type: str) -> list[str]:
        return list(self.fixture_cache[model_type].elements_by_name.keys())

    def get_content_item(
        self, model_type: str, uid: int | None = None, name: str | None = None
    ) -> dict:
        if uid is not None:
            return self.fixture_cache[model_type].query_id(uid)
        if name is not None:
            return self.fixture_cache[model_type].query_name(name)
        raise ValueError("Query needs either uid or name of object")

    def _try_inheritance(
        self, model_type: str, values: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        try:
            return self.fixture_cache[model_type].inheritance(values)
        except KeyError:
            log.error(f"Query failed - model-type {model_type} is unknown")
            return values, []
