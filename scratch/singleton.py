"""Test-Construct for a replacing singleton.

- Core-Lib uses a default fixtureClient
- default client gets replaced as soon as user instantiates another client
- that can happen just with an instantiation`WebClient`

"""
from abc import ABC, abstractmethod
from typing import Optional, Self, Unpack, TypedDict


class AbcClient(ABC):
    """AbstractBase-Class to access a testbed instance."""

    _instance: Optional[Self] = None

    def __init__(self) -> None:
        print("ABC init")
        global tb_client
        tb_client = self

    @classmethod
    def __new__(cls, *_args: tuple, **_kwargs: Unpack[TypedDict]) -> Self:
        # Singleton, TODO: overwrite / exchange
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            print("ABC-Singleton created")
        else:
            print("ABC-Singleton reused")
        return cls._instance

    def __del__(self) -> None:
        AbcClient._instance = None

    @abstractmethod
    def do_something(self) -> None:
        print("ABC do")


class FixClient(AbcClient):
    """Client-Class to access the file based fixtures."""

    def __init__(self) -> None:
        super().__init__()
        print("Fix Init")

    def do_something(self) -> None:
        print("Fix do")


class WebClient(AbcClient):
    """Client-Class to access the file based fixtures."""

    def __init__(self) -> None:
        super().__init__()
        print("Web Init")

    def do_something(self) -> None:
        print("Web do")


print("####### TB - default to fix ##########")
tb_client = FixClient()
tb_client.do_something()

print("####### Web ##########")
web_client = WebClient()
web_client.do_something()

print("####### TB - also web now ##########")
tb_client.do_something()

print("####### TB - overwritten with fix ##########")
FixClient()
tb_client.do_something()
