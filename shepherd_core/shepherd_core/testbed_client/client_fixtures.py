from typing import List
from typing import Optional

from ..data_models.base.shepherd import ShpModel
from ..data_models.base.wrapper import Wrapper
from .client_abc import AbcClient
from .fixtures import Fixtures


class FixturesClient(AbcClient):
    """Client-Class to access the file based fixtures."""

    def __init__(self) -> None:
        # super().__init__()
        self._fixtures: Optional[Fixtures] = Fixtures()

    def insert(self, data: ShpModel) -> bool:
        wrap = Wrapper(
            datatype=type(data).__name__,
            parameters=data.model_dump(),
        )
        self._fixtures.insert_model(wrap)
        return True

    def query_ids(self, model_type: str) -> List[int]:
        return list(self._fixtures[model_type].elements_by_id.keys())

    def query_names(self, model_type: str) -> List[str]:
        return list(self._fixtures[model_type].elements_by_name.keys())

    def query_item(
        self, model_type: str, uid: Optional[int] = None, name: Optional[str] = None
    ) -> dict:
        if uid is not None:
            return self._fixtures[model_type].query_id(uid)
        if name is not None:
            return self._fixtures[model_type].query_name(name)
        raise ValueError("Query needs either uid or name of object")

    def try_inheritance(self, model_type: str, values: dict) -> (dict, list):
        return self._fixtures[model_type].inheritance(values)

    def try_completing_model_old(self, model_type: str, values: dict) -> (dict, list):
        """Init by name/id, for none existing instances raise Exception.

        TODO: remove!!
        """
        if len(values) == 1 and next(iter(values.keys())) in {"id", "name"}:
            value = next(iter(values.values()))
            if (
                isinstance(value, str)
                and value.lower() in self._fixtures[model_type].elements_by_name
            ):
                values = self.query_item(model_type, name=value)
            elif isinstance(value, int) and value in self._fixtures[model_type].elements_by_id:
                values = self.query_item(model_type, uid=value)
            else:
                msg = f"Query {model_type} by name / ID failed - {values} is unknown!"
                raise ValueError(msg)
        return self.try_inheritance(model_type, values)

    def fill_in_user_data(self, values: dict) -> dict:
        # hotfix until testbed.client is working, TODO
        if values.get("owner") is None:
            values["owner"] = "unknown"
        if values.get("group") is None:
            values["group"] = "unknown"
        return values
