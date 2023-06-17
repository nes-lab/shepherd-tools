from pathlib import Path
from typing import Union, Optional

import requests
from pydantic import validate_arguments


from .commons import testbed_server_default
from .data_models.base.shepherd import ShpModel
from .data_models.base.wrapper import Wrapper
from .data_models.base.fixture import Fixtures
#from .data_models.testbed.user import User

class User:
    pass

class TestbedClient:

    _instance = None

    def __init__(self, **kwargs):
        if not hasattr(self, "_token"):
            self._token: str = "null"
            self._server: Optional[str] = testbed_server_default
            self._user: Optional[User] = None
            self._key: Optional[str] = None
            self._fixtures: Optional[Fixtures] = None
        if "server" in kwargs or "token" in kwargs:
            self.connect(**kwargs)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TestbedClient, cls).__new__(cls)
        return cls._instance

    def __del__(self):
        TestbedClient._instance = None

    @validate_arguments
    def connect(self, server: Optional[str] = None, token: Union[str, Path, None] = None) -> bool:
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
            if "demo_fixture" == server.lower():
                self._server = None
            else:
                self._server = server.lower()

        if self._server:
            # extended connection-test:
            self._query_session_key()
            return self._query_user_data()
        else:
            self._fixtures = Fixtures()

        return True

    def insert(self, data: ShpModel) -> bool:
        wrap = Wrapper(
            datatype=type(data).__name__,
            parameters=data.dict(),
        )
        if self._server:
            r = requests.post(self._server + "/add", data=wrap.json())
            r.raise_for_status()
        elif self._fixtures:
            self._fixtures.insert_model(wrap)
        else:
            raise RuntimeError("Not Implemented, TODO")
        return True

    def query(self, model_type: str, uid: Optional[int] = None, name: Optional[str] = None) -> dict:
        if self._server:
            raise RuntimeError("Not Implemented, TODO")
        else:
            if uid:
                return self._fixtures[model_type].query_id(uid)
            if name:
                return self._fixtures[model_type].query_name(name)
            else:
                raise ValueError("Query needs either uid or name of object")

    def _query_session_key(self) -> bool:
        if self._server:
            r = requests.get(self._server + "/session_key")
            r.raise_for_status()
            self._key = r.json()["value"]  # TODO: not finished
            return True
        return False

    def _query_user_data(self) -> bool:
        if self._server:
            r = requests.get(self._server + "/user?token=" + self._token)
            # TODO: possibly a security nightmare (send via json or encrypted via public key?)
            r.raise_for_status()
            self._user = User(**r.json())
            return True
        return False

    def inheritance(self, model_type: str, values: dict) -> (dict, list):
        if self._server:
            raise RuntimeError("Not Implemented, TODO")
        else:
            return self._fixtures[model_type].inheritance(values)

    def add_account_data(self, values: dict) -> dict:
        if self._user:
            if values.get("owner"):
                values["owner"] = self._user.name
            if values.get("group"):
                values["group"] = self._user.group
        return values


tb_client = TestbedClient()
