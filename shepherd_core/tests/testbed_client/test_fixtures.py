from shepherd_core.testbed_client.fixtures import Fixtures


def test_validity_fixtures() -> None:
    Fixtures(reset=True, validate=True)
    # TODO: could also instantiate complete models
