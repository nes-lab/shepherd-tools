"""


Fixtures == OffLineDemoInstances
now:	core	fixtClient
inter:	core	webClient	webSrv	fixtClient
final:	core	webClient	webSrv	DbClient

Users, Sheep and ServerApps should have access to the same DB via WebClient

Comfort functions:
- fixtures to DB, and vice versa

"""
from abc import ABC
from abc import abstractmethod
from typing import List
from typing import Optional
from typing import TypedDict

from typing_extensions import Self
from typing_extensions import Unpack

from shepherd_core.data_models import ShpModel


class AbcClient(ABC):
    _instance: Optional[Self] = None

#    def __init__(self) -> None:
#        pass

    @classmethod
    def __new__(cls, *_args: tuple, **_kwargs: Unpack[TypedDict]) -> Self:
        # Singleton, TODO: overwrite / exchange
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __del__(self) -> None:
        AbcClient._instance = None

    @abstractmethod
    def insert(self, data: ShpModel) -> bool:
        # this is also replace!
        pass

    @abstractmethod
    def query_ids(self, model_type: str) -> List[int]:
        pass

    @abstractmethod
    def query_names(self, model_type: str) -> List[str]:
        pass

    @abstractmethod
    def query_item(
        self, model_type: str, uid: Optional[int] = None, name: Optional[str] = None
    ) -> dict:
        pass

    @abstractmethod
    def try_inheritance(self, model_type: str, values: dict) -> (dict, list):
        # TODO: maybe internal? yes
        pass

    def try_completing_model(self, model_type: str, values: dict) -> (dict, list):
        """Init by name/id, for none existing instances raise Exception.

        This is the main entry-point for querying a model (used be the core-lib).
        """
        if len(values) == 1 and next(iter(values.keys())) in {"id", "name"}:
            try:
                values = self.query_item(model_type, name=values.get("name"), uid=values.get("id"))
            except ValueError as err:
                raise ValueError(
                    "Query %s by name / ID failed - %s is unknown!", model_type, values
                ) from err
        return self.try_inheritance(model_type, values)

    @abstractmethod
    def fill_in_user_data(self, values: dict) -> dict:
        # TODO: is it really helpful and needed?
        pass
