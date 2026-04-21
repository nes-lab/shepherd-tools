import pytest
from shepherd_core.data_models.content import content_supported
from shepherd_core.data_models.content import instantiate_content
from shepherd_core.data_models.testbed import components_supported
from shepherd_core.data_models.testbed import instantiate_component
from shepherd_core.testbed_client import tb_client
from shepherd_core.testbed_client.fixtures import Fixtures


def test_fixtures_validity() -> None:
    Fixtures(reset=True, validate=True)


@pytest.mark.parametrize("model_type", tb_client.list_resource_types())
def test_fixtures_visibility(model_type: str) -> None:
    tb_client.fixture_cache.complete_fixtures()
    if model_type.lower() not in content_supported:
        return
    content_names = tb_client.list_resource_names(model_type)
    for content_name in content_names:
        model_data = tb_client.get_resource_item(model_type, name=content_name)
        assert model_data.get("visible2all", False)
        # tests below automatically tested for visible content
        assert model_data.get("owner") is not None
        assert model_data.get("group") is not None


def test_fixtures_are_components_or_content() -> None:
    c_and_c = set(content_supported.keys()) | set(components_supported.keys())
    fixture_types = tb_client.list_resource_types()
    assert len(set(fixture_types)) == len(fixture_types)
    assert len(set(fixture_types) & c_and_c) == len(set(fixture_types))


@pytest.mark.parametrize(
    "model_type", set(tb_client.list_resource_types()) & set(content_supported.keys())
)
def test_fixtures_instantiate_content(model_type: str) -> None:
    content_names = tb_client.list_resource_names(model_type)
    for content_name in content_names:
        model_data = tb_client.get_resource_item(model_type, name=content_name)
        model = instantiate_content(model_type, model_data)
        assert model is not None


@pytest.mark.parametrize(
    "model_type", set(tb_client.list_resource_types()) & set(content_supported.keys())
)
def test_fixtures_instantiate_contents(model_type: str) -> None:
    content_names = tb_client.list_resource_names(model_type)
    for content_name in content_names:
        model_data = tb_client.get_resource_item(model_type, name=content_name)
        model = instantiate_content(model_type, model_data)
        assert model is not None


@pytest.mark.parametrize(
    "model_type", set(tb_client.list_resource_types()) & set(components_supported.keys())
)
def test_fixtures_instantiate_components(model_type: str) -> None:
    content_names = tb_client.list_resource_names(model_type)
    for content_name in content_names:
        model_data = tb_client.get_resource_item(model_type, name=content_name)
        model = instantiate_component(model_type, model_data)
        assert model is not None
