from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic import IPvAnyAddress
from pydantic import confloat
from pydantic import constr
from pydantic import root_validator

from ..base.content import id_int
from ..base.content import name_str
from ..base.content import safe_str
from ..base.fixture import Fixtures
from ..base.shepherd import ShpModel
from .cape import Cape
from .cape import TargetPort
from .target import Target

fixture_path = Path(__file__).resolve().with_name("observer_fixture.yaml")
fixtures = Fixtures(fixture_path, "observer")

mac_str = constr(max_length=17, regex=r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")


class Observer(ShpModel, title="Shepherd-Sheep"):
    """meta-data representation of a testbed-component (physical object)"""

    id: id_int  # noqa: A003
    name: name_str
    description: safe_str
    comment: Optional[safe_str] = None

    ip: IPvAnyAddress
    mac: mac_str

    room: name_str
    eth_port: name_str

    latitude: confloat(ge=-90, le=90) = 51.026573  # cfaed
    longitude: confloat(ge=-180, le=180) = 13.723291

    cape: Optional[Cape]
    target_a: Optional[Target]
    target_b: Optional[Target] = None

    created: datetime = Field(default_factory=datetime.now)
    alive_last: Optional[datetime]

    def __str__(self):
        return self.name

    @root_validator(pre=True)
    def from_fixture(cls, values: dict) -> dict:
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        return values

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
        has_cape = values["cape"] is not None
        has_target = (values["target_a"] is not None) or (
            values["target_b"] is not None
        )
        if not has_cape and has_target:
            raise ValueError(
                f"Observer '{values['name']}' is faulty " f"-> has targets but no cape"
            )
        return values

    def get_target_port(self, target_id: int) -> TargetPort:
        if self.target_a is not None and target_id == self.target_a.id:
            return TargetPort.A
        if self.target_b is not None and target_id == self.target_b.id:
            return TargetPort.B
        raise ValueError(
            f"Target-ID {target_id} was not found in Observer '{self.name}'"
        )
