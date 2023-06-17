## Datastructure

### Features

- new orchestration ``/data-models`` with focus on remote shepherd-testbed
- classes of sub-models
  - ``/base``: base-classes, configuration and -functionality for all models
  - ``/testbed``: meta-data representation of all testbed-components
  - ``/content``: reusable meta-data for fw, h5 and vsrc-definitions
  - ``/experiment``: configuration-models including sub-systems
  - ``/task``: digestible configs for shepherd-herd or -sheep
- fixtures selectable by name & ID
- fixtures support inheritance
- behavior controlled by ``ShpModel``
- models support
  - auto-completion with neutral / sensible values
  - complex and custom datatypes (ie. PositiveInt, lists checks on length)
  - checking of inputs and type-casting
  - generate their own schema (for web-forms)
  - pre-validation where possible
  - load/store to yaml with typecheck through wrapper
  - documentation
- experiment-definition should be secure
  - types are limited in size (str)
  - exposes no internal paths
- experiments can be transformed to task-sets (``TestbedTasks.from_xp()``)


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
- @kai
  - firmwares
  - programmer-ports determine IC
    - memory read - family-code, or write factory
  - when tracing v_intermediate, also this current, or output?
- ``objcopy -O ihex input.elf output.hex``
  - ``-S`` will strip useless sections
  - ``-I ihex -O elf32-littlearm`` for reversal is also possible
    - TODO: try to find ``objdump -t [elf_file] | grep SHEPHERD_NODE_ID``

- title in class might be rubbish

- Warn about tricky syntax
  - defining sub-data-models in an experiment in python:
    - experiments-default: don't mention argument in init
    - trace-default: init trace with empty argument list
    - disable: init with "None"
  - defining experiment in yaml:
    - experiment-default: don't mention it
    - trace-default: NOT POSSIBLE, right?
    - disable: init with "null" OR just mention parameter but keep it empty

## Pydantic-Pitfalls (<v2)

- ``@root_validator`` does not get an extra ``@classmethod``

### add documentation after creation -> avoid Field()

- these do not work

```Python
from pydantic import Field
from shepherd_core.data_models import ShpModel

class Experiment(ShpModel, title="Config of an Experiment"):
    def __init__(self):  # test to add doc after creation -> to avoid Field()
        super().__init__()
        self.Config.fields["output_path"].description = "test description"
    class Config:
        fields: dict[str, Field] = {}
        fields["output_path"] = Field(description="test description")
```

### simplify init of pydantic-class

What I want: init a fixture-class with Class("name") or Class(ID) instead of Class(name="name")

What does not work:

```Python
from pathlib import Path
from typing import Union
from pydantic import root_validator
from shepherd_core.data_models import Fixture
from shepherd_core.data_models import ShpModel

fixtures = Fixture(Path("fix.yaml"), "testbed.target")


class Target(ShpModel, title="Target Node (DuT)"):
    @root_validator(pre=True)
    def query_database(cls, values: Union[dict, str, int]):
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        return values
```

what might work:

- writing a custom __init__() and putting lookup() there
- wait for V2
