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


### real world models

- testbed
- observer
- cape
- target
- MCU


## TODO

- establish internal variables ``_var``

## Pydantic-Pitfalls (<v2)

- ``@root_validator`` does not get an extra ``@classmethod``
