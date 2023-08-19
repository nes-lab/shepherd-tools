from datetime import timedelta
from pathlib import Path
from typing import List
from typing import Optional

from pydantic import Field
from pydantic import HttpUrl
from pydantic import model_validator
from typing_extensions import Annotated

from ...testbed_client import tb_client
from ..base.content import IdInt
from ..base.content import NameStr
from ..base.content import SafeStr
from ..base.shepherd import ShpModel
from .observer import Observer


class Testbed(ShpModel):
    """meta-data representation of a testbed-component (physical object)"""

    id: IdInt  # noqa: A003
    name: NameStr
    description: SafeStr
    comment: Optional[SafeStr] = None

    url: Optional[HttpUrl] = None

    observers: Annotated[List[Observer], Field(min_length=1, max_length=64)]

    shared_storage: bool = True
    data_on_server: Path
    data_on_observer: Path
    # ⤷ storage layout: root_path/content_type/group/owner/[object]

    prep_duration: timedelta = timedelta(minutes=5)
    # TODO: one BBone is currently time-keeper

    @model_validator(mode="before")
    @classmethod
    def query_database(cls, values: dict) -> dict:
        values, _ = tb_client.try_completing_model(cls.__name__, values)
        return values

    @model_validator(mode="after")
    def post_validation(self):
        observers = []
        ips = []
        macs = []
        capes = []
        targets = []
        eth_ports = []
        for _obs in self.observers:
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
            raise ValueError("Observers-MAC-Address used more than once in Testbed")
        if len(capes) > len(set(capes)):
            raise ValueError("Cape used more than once in Testbed")
        if len(targets) > len(set(targets)):
            raise ValueError("Target used more than once in Testbed")
        if len(eth_ports) > len(set(eth_ports)):
            raise ValueError("Observers-Ethernet-Port used more than once in Testbed")
        if self.prep_duration.total_seconds() < 0:
            raise ValueError("Task-Duration can't be negative.")
        if not self.shared_storage:
            raise ValueError("Only shared-storage-option is implemented")
        return self

    def get_observer(self, target_id: int) -> Observer:
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
