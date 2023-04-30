## Datastructure

### Features

- fixtures selectable by name & ID
- fixtures support inheritance
- behavior controlled by ``ShpModel``
- models support
  - auto-completion with neutral / sensible values
  - checking of inputs and type-casting
  - generate their own schema (for web-forms)
  - pre-validation
- experiment-definition should be secure
  - types are limited in size (str)
  - exposes no internal paths

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
- descriptions to fields (docstring on sub-models)
- @kai
  - firmwares
  - programmer-ports determine IC
    - memory read - family-code, or write factory
- converter for
  - pre-tasks (copying, programming)
  - emulation
  - post-tasks (copying, transformations, cleaning)
    - feature-tasks
    - email results
- ``objcopy -O ihex input.elf output.hex``
  - ``-S`` will strip useless sections
  - ``-I ihex -O elf32-littlearm`` for reversal is also possible
    - TODO: try to find ``objdump -t [elf_file] | grep SHEPHERD_NODE_ID``

- title in class might be rubbish

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
from shepherd_core.data_models import Fixtures
from shepherd_core.data_models import ShpModel

fixtures = Fixtures(Path("fix.yaml"), "testbed.target")
class Target(ShpModel, title="Target Node (DuT)"):
    @root_validator(pre=True)
    def from_fixture(cls, values: Union[dict, str, int]):
        values = fixtures.lookup(values)
        values, chain = fixtures.inheritance(values)
        return values
```

what might work:

- writing a custom __init__() and putting lookup() there
- wait for V2
