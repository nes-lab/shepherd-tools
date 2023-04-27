from datetime import datetime
from pathlib import Path
from typing import Optional
from typing import Union

from pydantic import Field
from pydantic import IPvAnyAddress
from pydantic import confloat
from pydantic import constr
from pydantic import root_validator

from .. import Fixtures
from .. import ShpModel
from .cape import Cape
from .target import Target

fixture_path = Path(__file__).resolve().with_name("observer_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed.observer")


class Observer(ShpModel, title="Shepherd-Sheep"):
    """meta-data representation of a testbed-component (physical object)"""

    uid: constr(
        strip_whitespace=True,
        to_lower=True,
        min_length=4,
        max_length=16,
    )

    name: constr(max_length=32)
    description: str
    comment: Optional[str] = None

    ip: IPvAnyAddress
    mac: constr(max_length=17)  # TODO

    room: constr(max_length=32) = ""
    eth_port: constr(max_length=32) = ""

    latitude: confloat(ge=-90, le=90) = 51.026573  # cfaed
    longitude: confloat(ge=-180, le=180) = 13.723291

    cape: Cape
    target_a: Target
    target_b: Optional[Target] = None

    created: datetime = Field(default_factory=datetime.now)
    alive_last: Optional[datetime]

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def recursive_fill(cls, values: Union[dict, str, int]):
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        return values
