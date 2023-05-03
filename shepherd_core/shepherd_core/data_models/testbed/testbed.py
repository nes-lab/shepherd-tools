from datetime import timedelta
from pathlib import Path
from typing import Optional

from pydantic import conlist
from pydantic import root_validator

from ..base.content import id_int
from ..base.content import name_str
from ..base.content import safe_str
from ..base.fixture import Fixtures
from ..base.shepherd import ShpModel
from .observer import Observer

fixture_path = Path(__file__).resolve().with_name("testbed_fixture.yaml")
fixtures = Fixtures(fixture_path, "testbed")


class Testbed(ShpModel):
    """meta-data representation of a testbed-component (physical object)"""

    id: id_int  # noqa: A003
    name: name_str
    description: safe_str
    comment: Optional[safe_str] = None

    observers: conlist(item_type=Observer, min_items=1, max_items=64)

    shared_storage: bool = True
    data_on_server: Path
    data_on_observer: Path
    # ⤷ storage layout: root_path/content_type/group/owner/[object]

    prep_duration: timedelta = timedelta(minutes=5)
    # TODO: one BBone is currently time-keeper

    @root_validator(pre=True)
    def from_fixture(cls, values: dict) -> dict:
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        return values

    @root_validator(pre=False)
    def post_validation(cls, values: dict) -> dict:
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

    def get_observer(self, target_id: int):
        for _observer in self.observers:
            has_tgt_a = _observer.target_a is not None
            if has_tgt_a and target_id == _observer.target_a.id:
                return _observer
            has_tgt_b = _observer.target_b is not None
            if has_tgt_b and target_id == _observer.target_b.id:
                return _observer
        raise ValueError(
            f"Target-ID {target_id} was not found in Testbed '{self.name}'"
        )
