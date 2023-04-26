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
- fixtures selectable by name & uid
-

## Pydantic-Pitfalls (<v2)

- ``@root_validator`` does not get an extra ``@classmethod``
