"""A basic web-client to access testbed-related content without a login.

NOTE: this is a direct copy of webservice/testbed-client

TODO: add caching-system that
    - saves online-data to local fixture and
    - directs the fixture-client to it IF connection is lost
"""

import copy
from collections.abc import Collection
from importlib import metadata
from typing import Any

import requests
from pydantic import HttpUrl
from pydantic import validate_call
from requests import JSONDecodeError
from requests import Response
from typing_extensions import Unpack

from shepherd_core.config import core_config
from shepherd_core.logger import increase_verbose_level
from shepherd_core.logger import log
from shepherd_core.testbed_client import AbcClient


class TestbedClient(AbcClient):
    """A client to pull status of testbed and get info about available resources.

    It basically processes all data that is available without logging in / authentication.

    Resources mean
    - content like energy-environments, virtual-source configurations, ...
    - testbed-components like target-boards, observer including positions, ...
    """

    __test__ = False  # tell pytest this is no unittest

    @validate_call
    def __init__(
        self,
        server: HttpUrl | str | None = None,
        timeout: int | None = None,
        *,
        debug: bool = False,
    ) -> None:

        if debug:
            increase_verbose_level(3)

        self._server = (
            HttpUrl(server) if server is not None else HttpUrl(core_config.TESTBED_SERVER)
        )
        self._auth: dict | None = None
        self._timeout: int = timeout if timeout is not None else core_config.TESTBED_TIMEOUT

        self.testbed_status()
        super().__init__()  # replaces default fixture-client
        core_config.testbed_name = self.testbed_name()
        core_config.validate_infrastructure = True

    def _req(self, method: str, route: str, **kwargs: Unpack[dict]) -> Response:
        """Preconfigured request that handles timeouts, authentication & most common exceptions."""
        # TODO: add retries?
        url = f"{self._server}{route.lstrip('/')}"
        try:
            return requests.request(
                method=method,
                url=url,
                headers=self._auth,
                timeout=self._timeout,
                **kwargs,
            )
        except requests.Timeout:
            msg = f"Request timed out on {method}({url})"
            raise ConnectionError(msg) from None
        except requests.ConnectionError:
            msg = f"Request failed with {method}({url})"
            raise ConnectionError(msg) from None

    @staticmethod
    def _msg(rsp: Response) -> str:
        """Transform response of request into a printable message."""
        try:
            return f"{rsp.reason} - {rsp.json()['detail']}"
        except JSONDecodeError:
            return f"{rsp.reason}"

    # ####################################################################
    # Testbed-Status
    # ####################################################################

    def testbed_status(self) -> bool:
        """Prints status of testbed-server and returns True is state is fine.

        Possible restrictions and warnings are explained in log.
        """
        rsp = self._req("get", "/")

        if not rsp.ok:
            log.warning("Failed to fetch status from WebApi: %s", self._msg(rsp))
            return False

        had_error = False
        state = rsp.json()
        scheduler = state.get("scheduler")
        if isinstance(scheduler, dict):
            active = scheduler.get("activated")
            if active is None:
                log.warning("Scheduler not active!")
                had_error = True
            dry_run = scheduler.get("dry_run")
            if dry_run:
                log.warning("Scheduler is running in demo-mode (dry-run)!")
                had_error = True
            targets_offline = scheduler.get("targets_offline")
            if isinstance(targets_offline, Collection) and len(targets_offline) > 0:
                log.warning("One or more targets seem to be offline: %s", targets_offline)
                had_error = True
            # TODO: could tests for last update being old
        if metadata.version("shepherd-client") != state.get("server_version"):
            log.warning(
                "Your client version does not match with server -> "
                "consider matching to avoid errors"
            )
            log.info(
                "client v%s vs server v%s",
                metadata.version("shepherd-client"),
                state.get("server_version"),
            )
        if metadata.version("shepherd-core") != state.get("core_version"):
            log.warning(
                "Your version of shepherd-core does not match with server -> "
                "consider matching to avoid errors"
            )
            log.info(
                "shepherd-core on client %s vs %s on server",
                metadata.version("shepherd-core"),
                state.get("core_version"),
            )
        restrictions = state.get("restrictions")
        if restrictions is None:
            restrictions = []
        for restriction in restrictions:
            log.warning("Active testbed-restriction: %s", restriction)
        return not had_error

    def testbed_name(self) -> str:
        rsp = self._req("get", "/testbed")
        if not rsp.ok:
            msg = (f"Failed to fetch status from WebApi: {self._msg(rsp)}",)
            raise ConnectionError(msg)
        state = rsp.json()
        return state.get("name")

    def testbed_restrictions(self) -> list[str]:
        rsp = self._req("get", "/testbed/restrictions")
        if not rsp.ok:
            log.warning("Query for restrictions failed with: %s", self._msg(rsp))
            return []
        data = rsp.json()
        if data is None:
            return []
        return rsp.json()

    # ####################################################################
    # Content & Component Models
    # ####################################################################

    def list_resource_types(self) -> list[str]:
        rsp = self._req("get", "/resources")
        if rsp is None or not rsp.ok:
            return []
        return rsp.json()

    def list_resource_ids(self, model_type: str) -> list[int]:
        """Note that testbed-components have no ID."""
        rsp = self._req("get", f"/resources/{model_type}")
        if not rsp.ok:
            return []
        return list(rsp.json().keys())

    def list_resource_names(self, model_type: str) -> list[str]:
        rsp = self._req("get", f"/resources/{model_type}")
        if not rsp.ok:
            return []
        return list(rsp.json().values())

    def get_resource_item(
        self, model_type: str, uid: int | None = None, name: str | None = None
    ) -> dict:
        # TODO: divide into by_id and by_name?
        rsp = self._req("get", f"/resources/{model_type}/{uid if uid is not None else name}")
        if not rsp.ok:
            return {}
        return rsp.json()

    def _try_inheritance(
        self, model_type: str, values: dict[str, Any], chain: list[str] | None = None
    ) -> tuple[dict[str, Any], list[str]]:
        """Copy of Fixture().inheritance()."""
        if chain is None:
            chain: list[str] = []
        values = copy.copy(values)
        post_process: bool = False
        fixture_base: dict = {}
        if "inherit_from" in values:
            fixture_name = values.pop("inherit_from")
            # ⤷ will also remove entry from dict
            if "name" in values and len(chain) < 1:
                base_name = str(values.get("name"))
                if base_name in chain:
                    msg = f"Inheritance-Circle detected ({base_name} already in {chain})"
                    raise ValueError(msg)
                if base_name == fixture_name:
                    msg = f"Inheritance-Circle detected ({base_name} == {fixture_name})"
                    raise ValueError(msg)
                chain.append(base_name)
            fixture_base = copy.copy(self[fixture_name])
            log.debug("'%s' will inherit from '%s'", model_type, fixture_name)
            fixture_base["name"] = fixture_name
            chain.append(fixture_name)
            base_dict, chain = self._try_inheritance(
                model_type=model_type, values=fixture_base, chain=chain
            )
            for key, value in values.items():
                # keep previous entries
                base_dict[key] = value
            values = base_dict

        # TODO: cleanup and simplify - use fill_mode() and line up with web-interface
        elif "name" in values and str(values.get("name")).lower() in self.list_resource_names(
            model_type
        ):
            fixture_name = str(values.get("name")).lower()
            fixture_base = copy.copy(self.get_resource_item(model_type, name=fixture_name))
            post_process = True

        elif values.get("id") in self.list_resource_ids(model_type):
            id_ = values["id"]
            fixture_base = copy.copy(self.get_resource_item(model_type, uid=id_))
            post_process = True

        if post_process:
            # last two cases need
            for key, value in values.items():
                # keep previous entries
                fixture_base[key] = value
            if "inherit_from" in fixture_base:
                log.error("Inheritance on server-data should not occur!")
                # TODO: test for that?
                # as long as this key is present this will act recursively
                chain.append(fixture_base["name"])
                values, chain = self._try_inheritance(model_type, values=fixture_base, chain=chain)
            else:
                values = fixture_base

        return values, chain
