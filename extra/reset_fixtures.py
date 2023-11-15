"""
this will re-populate the temporary database assembled from the yaml-fixtures
NOTE1: this will be done automatically IF database is older than 24h
NOTE2: only temporary, while testbed-client is a mockup
"""
from shepherd_core.testbed_client.fixtures import Fixtures


Fixtures(reset=True)
