## Datastructure

### experiment-structure

- basics
- scheduling
- **SystemLogger**
- ~~AuxPort~~
- TargetConfigs
  - Programming
  - PowerTracer
  - GpioTracer
  - GpioActuator
  - vSrc
    - vHarvester
    - [vConverter]

## TODO

- establish internal variables ``_var``
- descriptions to parameters (docstring on sub-models)

- Warn about tricky syntax
  - defining sub-data-models in an experiment in python:
    - experiments-default: don't mention argument in init
    - trace-default: init trace with empty argument list
    - disable: init with "None"
  - defining experiment in yaml:
    - experiment-default: don't mention it
    - trace-default: NOT POSSIBLE, right?
    - disable: init with "null" OR just mention parameter but keep it empty

### add documentation after creation ⇾ avoid Field()

- these do not work

```Python
from typing import Dict
from pydantic import Field
from shepherd_core.data_models import ShpModel

class Experiment(ShpModel, title="Config of an Experiment"):
    def __init__(self):  # test to add doc after creation ⇾ to avoid Field()
        super().__init__()
        self.Config.fields["output_path"].description = "test description"
    class Config:
        fields: Dict[str, Field] = {}
        fields["output_path"] = Field(description="test description")
```

### simplify init of pydantic-class

What I want: init a fixture-class with Class("name") or Class(ID) instead of Class(name="name")

What does not work:

```Python
from pathlib import Path
from typing import Union
from pydantic import model_validator
from shepherd_core.data_models import Fixture
from shepherd_core.data_models import ShpModel

fixtures = Fixture(Path("fix.yaml"), "testbed.target")


class Target(ShpModel, title="Target Node (DuT)"):
    @model_validator(mode="before")
    @classmethod
    def query_database(cls, values: Union[dict, str, int]):
        values, _ = fixtures.complete_resource_model(values)
        return values
```

what might work:

- writing a custom __init__() and putting lookup() there
- wait for V2
