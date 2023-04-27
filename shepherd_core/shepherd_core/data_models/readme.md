## Datastructure

### experiment models

!experiment
    !basics / schedule
    !programming
    emulator
        vsource
            vharvester
        power-logging (Features)
        gpio-logging
        sys-logging
    targetCfg

### real world models

- Testbed
- Observer
- Cape
- Target
- MCU
- Firmware


## TODO

- establish internal variables ``_var``
+ fixtures selectable by name & uid
+ limit all strings
- add descriptions to fixtures
- descriptions to fields (docstring on sub-models)
- @kai
  - firmwares
  - programmer-ports determine IC
    - memory read - family-code, or write factory
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
class Experiment(ShpModel, title="Config of an Experiment"):
    def __init__(self):  # test to add doc after creation -> to avoid Field()
        super().__init__()
        self.Config.fields["output_path"].description = "test description"
    class Config:
        fields: dict[str, Field] = {}
        fields["output_path"] = Field(description="test description")
```

### simplify init of pydantic-class

What I want: init a fixture-class with Class("name") or Class(uid) instead of Class(name="name")

What does not work:

```Python
class Target(ShpModel, title="Target Node (DuT)"):
    @root_validator(pre=True)
    def recursive_fill(cls, values: Union[dict, str, int]):
        values = fixtures.lookup(values)  # TODO: a (non-working) test for now
        values, chain = fixtures.inheritance(values)
```

what might work:

- writing a custom __init__() and putting lookup() there
- wait for V2
