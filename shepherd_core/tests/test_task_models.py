from shepherd_core.data_models.task.emulation import EmulationTask


def test_experiment_model_min_observer():
    EmulationTask(
        input_path="./here",
    )
