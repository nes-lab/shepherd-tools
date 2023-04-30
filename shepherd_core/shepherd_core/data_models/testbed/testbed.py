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

    id: constr(to_lower=True, max_length=16)  # noqa: A003
    name: constr(max_length=32)
    description: str
    comment: Optional[str] = None

    observers: conlist(item_type=Observer, min_items=1, max_items=64)
    shared_storage: bool = True
    data_on_server: Path
    data_on_observer: Path
    # TODO: one BBone is currently time-keeper

    @root_validator(pre=True)
    def from_fixture(cls, values: dict):
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        return values

    @root_validator(pre=False)
    def post_validation(cls, values: dict):
        observers = []
        ips = []
        macs = []
        capes = []
        targets = []
        eth_ports = []
        for _obs in values["observers"]:
            observers.append(_obs.id)
            ips.append(_obs.ip)
            macs.append(_obs.mac)
            if _obs.cape is not None:
                capes.append(_obs.cape)
            if _obs.target_a is not None:
                targets.append(_obs.target_a)
            if _obs.target_b is not None:
                targets.append(_obs.target_b)
            eth_ports.append(_obs.eth_port)
        if len(observers) > len(set(observers)):
            raise ValueError("Observers used more than once in Testbed")
        if len(ips) > len(set(ips)):
            raise ValueError("Observer-IP used more than once in Testbed")
        if len(macs) > len(set(macs)):
            raise ValueError("Observers-MAC-Addresse used more than once in Testbed")
        if len(capes) > len(set(capes)):
            raise ValueError("Cape used more than once in Testbed")
        if len(targets) > len(set(targets)):
            raise ValueError("Target used more than once in Testbed")
        if len(eth_ports) > len(set(eth_ports)):
            raise ValueError("Observers-Ethernet-Port used more than once in Testbed")
        return values
