from shepherd_core.data_models.experiment.virtual_harvester import VirtualHarvester
from shepherd_core.data_models.experiment.virtual_harvester import fixtures as fix_hrv
from shepherd_core.data_models.experiment.virtual_source import VirtualSource
from shepherd_core.data_models.experiment.virtual_source import fixtures as fix_src


def test_experiment_fixture_vsrc():
    for fix in fix_src:
        name = fix["name"]
        VirtualSource(name=name)
        uid = fix["uid"]
        VirtualSource(uid=uid)


def test_experiment_fixture_vhrv():
    for fix in fix_hrv:
        name = fix["name"]
        if name == "neutral":
            continue
        VirtualHarvester(name=name)
        uid = fix["uid"]
        VirtualHarvester(uid=uid)
