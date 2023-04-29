from pathlib import Path
from typing import Optional

from pydantic import conlist
from pydantic import constr
from pydantic import root_validator

from ..base.fixture import Fixtures
from ..base.shepherd import ShpModel
from .observer import Observer

fixture_path = Path(__file__).resolve().with_name("testbed_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed.testbed")


class Testbed(ShpModel):
    """meta-data representation of a testbed-component (physical object)"""

    name: constr(max_length=32)
    uid: constr(to_lower=True, max_length=16)
    description: str
    comment: Optional[str] = None

    observers: conlist(item_type=Observer, min_items=1, max_items=64)
    shared_storage: bool = True
    data_on_server: Path
    data_on_observer: Path
    # TODO: one BBone is currently time-keeper

    @root_validator(pre=True)
    def recursive_fill(cls, values: dict):
        values, chain = fixtures.inheritance(values)
        return values
