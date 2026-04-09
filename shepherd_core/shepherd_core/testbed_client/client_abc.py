"""AbstractBase-Class of Client.

Fixtures == OffLineDemoInstances
offline:	core  - fixtClient
webDev:	    core  - webClient  <->	webSrv - fixtClient
webUser:	core  - webClient  <->  webSrv - DbClient
webInfra:   core  - webClient+ <->  webSrv - DbClient

Users, Sheep and ServerApps should have access to the same DB via WebClient

Note: ABC and FixClient can't be in separate files when tb_client should
      default to FixClient (circular import)
"""

from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import final

from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.logger import log


class AbcClient(ABC):
    """AbstractBase-Class to access a testbed instance."""

    def __init__(self) -> None:
        global tb_client  # noqa: PLW0603
        tb_client = self

    @abstractmethod
    def insert(self, data: ShpModel) -> bool:
        """Insert (and probably replace) entry.

        TODO: fixtures get replaced, but is that wanted for web?
        """

    @abstractmethod
    def query_ids(self, model_type: str) -> list[int]:
        pass

    @abstractmethod
    def query_names(self, model_type: str) -> list[str]:
        pass

    @abstractmethod
    def query_item(self, model_type: str, uid: int | None = None, name: str | None = None) -> dict:
        pass

    @abstractmethod
    def try_inheritance(
        self, model_type: str, values: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        # TODO: maybe internal? yes
        pass

    @final
    def try_completing_model(
        self, model_type: str, values: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        """Init by name/id, for none existing instances raise Exception.

        This is the main entry-point for querying a model (used be the core-lib).
        """
        if len(values) == 1 and next(iter(values.keys())) in {"id", "name"}:
            try:
                values = self.query_item(model_type, name=values.get("name"), uid=values.get("id"))
            except ValueError as err:
                msg = f"Query {model_type} by name / ID failed - {values} is unknown!"
                raise ValueError(msg) from err
            except KeyError:
                log.error(f"Query failed - model-type {model_type} is unknown")
                return values, []
        return self.try_inheritance(model_type, values)

    @abstractmethod
    def fill_in_user_data(self, values: dict[str, Any]) -> dict[str, Any]:
        # TODO: is it really needed and helpful?
        pass
