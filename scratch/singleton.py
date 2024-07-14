"""Test-Construct for a replacing singleton.

- Core-Lib uses a default fixtureClient
- default client gets replaced as soon as user instantiates another client
- that can happen just with an instantiation`WebClient`

"""

from abc import ABC
from abc import abstractmethod
from typing import Optional


class AbcClient(ABC):
    """AbstractBase-Class to access a testbed instance."""

    def __init__(self) -> None:
        print("ABC init")
        global tb_client
        tb_client = self

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
    """Client-Class to access the Web-Server."""

    def __init__(self) -> None:
        super().__init__()
        print("Web Init")

    def do_something(self) -> None:
        print("Web do")


tb_client: Optional[AbcClient] = None

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
