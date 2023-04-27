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

## Pydantic-Pitfalls (<v2)

- ``@root_validator`` does not get an extra ``@classmethod``
