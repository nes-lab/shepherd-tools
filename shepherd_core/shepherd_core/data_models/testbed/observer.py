import ipaddress
from datetime import datetime
from pathlib import Path
from typing import Optional
from typing import Union

from pydantic import Field
from pydantic import root_validator

from .. import Fixtures
from .. import ShpModel
from .cape import Cape
from .target import Target

fixture_path = Path(__file__).resolve().with_name("observer_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed.observer")


class Observer(ShpModel):
    name: str
    description: str
    comment: Optional[str] = None

    ip: ipaddress.IPv4Address = ""
    mac: str = ""  # TODO

    room: str = ""
    eth_port: str = ""

    latitude: float = 51.026573  # cfaed
    longitude: float = 13.723291

    cape: Union[str, Cape] = ""
    target_a: Union[str, Target] = ""
    target_b: Union[str, Target] = ""

    alive_last: datetime
    created: datetime = Field(default_factory=datetime.now)

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        return values
