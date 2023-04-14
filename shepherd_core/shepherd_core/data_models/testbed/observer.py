import ipaddress
from datetime import datetime
from typing import Union

from pydantic import Field, root_validator

from .cape import Cape
from .target import Target
from shepherd_core.data_models.model_fixture import Fixtures
from shepherd_core.data_models.model_shepherd import ShpModel

fixtures = Fixtures("observer_fixture.yaml", "testbed.observer")


class Observer(ShpModel):

    name: str
    description: str = ""
    comment: str = ""

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
