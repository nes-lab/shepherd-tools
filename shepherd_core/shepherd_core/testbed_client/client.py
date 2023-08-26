from importlib import import_module
from pathlib import Path
from typing import Optional
from typing import Union

from pydantic import validate_call

from ..commons import testbed_server_default
from ..data_models.base.shepherd import ShpModel
from ..data_models.base.wrapper import Wrapper
from .fixtures import Fixtures
from .user_model import User


class TestbedClient:
    _instance = None

    def __init__(self, **kwargs):
        if not hasattr(self, "_token"):
            self._token: str = "null"
            self._server: Optional[str] = testbed_server_default
            self._user: Optional[User] = None
            self._key: Optional[str] = None
            self._fixtures: Optional[Fixtures] = Fixtures()
            self._connected: bool = False
            self._req = None
        if "server" in kwargs or "token" in kwargs:
            self.connect(**kwargs)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __del__(self):
        TestbedClient._instance = None

    @validate_call
    def connect(
        self, server: Optional[str] = None, token: Union[str, Path, None] = None
    ) -> bool:
        """
        server: either "local" to use demo-fixtures or something like "https://HOST:PORT"
        token: your account validation
        """
        if isinstance(token, Path):
            with open(token.resolve()) as file:
                self._token = file.read()
        elif isinstance(token, str):
            self._token = token

        if server:
            self._server = server.lower()

        if self._server:
            self._req = import_module("requests")  # here due to slow startup

            # extended connection-test:
            self._query_session_key()
            self._connected = True
            return self._query_user_data()

        return True

    def insert(self, data: ShpModel) -> bool:
        wrap = Wrapper(
            datatype=type(data).__name__,
            parameters=data.model_dump(),
        )
        if self._connected:
            r = self._req.post(
                self._server + "/add", data=wrap.model_dump_json(), timeout=2
            )
            r.raise_for_status()
        else:
            self._fixtures.insert_model(wrap)
        return True

    def query_ids(self, model_type: str) -> list:
        if self._connected:
            raise RuntimeError("Not Implemented, TODO")
        return list(self._fixtures[model_type].elements_by_id.keys())

    def query_names(self, model_type: str) -> list:
        if self._connected:
            raise RuntimeError("Not Implemented, TODO")
        return list(self._fixtures[model_type].elements_by_name.keys())

    def query_item(
        self, model_type: str, uid: Optional[int] = None, name: Optional[str] = None
    ) -> dict:
        if self._connected:
            raise RuntimeError("Not Implemented, TODO")
        if uid:
            return self._fixtures[model_type].query_id(uid)
        if name:
            return self._fixtures[model_type].query_name(name)
        raise ValueError("Query needs either uid or name of object")

    def _query_session_key(self) -> bool:
        if self._server:
            r = self._req.get(self._server + "/session_key", timeout=2)
            r.raise_for_status()
            self._key = r.json()["value"]  # TODO: not finished
            return True
        return False

    def _query_user_data(self) -> bool:
        if self._server:
            r = self._req.get(self._server + "/user?token=" + self._token, timeout=2)
            # TODO: possibly a security nightmare (send via json or encrypted via public key?)
            r.raise_for_status()
            self._user = User(**r.json())
            return True
        return False

    def try_inheritance(self, model_type: str, values: dict) -> (dict, list):
        if self._connected:
            raise RuntimeError("Not Implemented, TODO")
        return self._fixtures[model_type].inheritance(values)

    def try_completing_model(self, model_type: str, values: dict) -> (dict, list):
        """init by name/id, for none existing instances raise Exception"""
        if len(values) == 1 and list(values.keys())[0] in ["id", "name"]:
            value = list(values.values())[0]
            if (
                isinstance(value, str)
                and value.lower() in self._fixtures[model_type].elements_by_name
            ):
                values = self.query_item(model_type, name=value)
            elif (
                isinstance(value, int)
                and value in self._fixtures[model_type].elements_by_id
            ):
                # TODO: still depending on _fixture
                values = self.query_item(model_type, uid=value)
            else:
                raise ValueError(
                    f"Query {model_type} by name / ID failed - " f"{values} is unknown!"
                )
        return self.try_inheritance(model_type, values)

    def fill_in_user_data(self, values: dict) -> dict:
        if self._user:
            if values.get("owner"):
                values["owner"] = self._user.name
            if values.get("group"):
                values["group"] = self._user.group
        return values


tb_client = TestbedClient()
