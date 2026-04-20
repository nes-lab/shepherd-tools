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

from typing_extensions import deprecated

from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.logger import log


class AbcClient(ABC):
    """AbstractBase-Class to access a testbed instance."""

    def __init__(self) -> None:
        global tb_client  # noqa: PLW0603
        tb_client = self

    def insert_content(self, data: ShpModel) -> bool:  # noqa: ARG002
        """Insert (and probably replace) entry."""
        log.warning("Missing account-details or capabilities for that storing content.")
        return False

    @abstractmethod
    def list_content_types(self) -> list[str]:
        """Get list of content types."""

    @abstractmethod
    def list_content_ids(self, model_type: str) -> list[int]:
        """Get list with all IDs of that content type."""

    @abstractmethod
    def list_content_names(self, model_type: str) -> list[str]:
        """Get list with all names of that content type."""

    @abstractmethod
    def get_content_item(
        self, model_type: str, uid: int | None = None, name: str | None = None
    ) -> dict:
        """Get model-parameters of that content fitting the type & name or ID."""

    @abstractmethod
    def _try_inheritance(
        self, model_type: str, values: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        pass

    @final
    def complete_content_model(
        self, model_type: str, values: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        """Init by name/id, for none existing instances raise Exception.

        This is the main entry-point for querying a model (used be the core-lib).
        """
        if len(values) == 1 and next(iter(values.keys())) in {"id", "name"}:
            try:
                values = self.get_content_item(
                    model_type, name=values.get("name"), uid=values.get("id")
                )
            except ValueError as err:
                msg = f"Query {model_type} by name / ID failed - {values} is unknown!"
                raise ValueError(msg) from err
            except KeyError:
                log.error(f"Query failed - model-type {model_type} is unknown")
                return values, []
        return self._try_inheritance(model_type, values)

    @deprecated("use .insert_content() instead")
    def insert(self, data: ShpModel) -> bool:
        return self.insert_content(data)

    @deprecated("use .list_content_types() instead")
    def query_types(self) -> list[str]:
        return self.list_content_types()

    @deprecated("use .list_content_ids() instead")
    def query_ids(self, model_type: str) -> list[int]:
        return self.list_content_ids(model_type)

    @deprecated("use .list_content_names() instead")
    def query_names(self, model_type: str) -> list[str]:
        return self.list_content_names(model_type)

    @deprecated("use .get_content_item() instead")
    def query_item(self, model_type: str, uid: int | None = None, name: str | None = None) -> dict:
        return self.get_content_item(model_type, uid=uid, name=name)

    @deprecated("use .complete_content_model() instead")
    def try_completing_model(
        self, model_type: str, values: dict[str, Any]
    ) -> tuple[dict[str, Any], list[str]]:
        return self.complete_content_model(model_type, values)
