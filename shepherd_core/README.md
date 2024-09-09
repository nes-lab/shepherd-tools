# Core Library

[![PyPiVersion](https://img.shields.io/pypi/v/shepherd_core.svg)](https://pypi.org/project/shepherd_core)
[![image](https://img.shields.io/pypi/pyversions/shepherd_core.svg)](https://pypi.python.org/pypi/shepherd-core)
[![Pytest](https://github.com/orgua/shepherd-datalib/actions/workflows/py_unittest.yml/badge.svg)](https://github.com/orgua/shepherd-datalib/actions/workflows/py_unittest.yml)
[![CodeStyle](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Main Documentation**: <https://orgua.github.io/shepherd>

**Source Code**: <https://github.com/orgua/shepherd-datalib>

**Main Project**: <https://github.com/orgua/shepherd>

---

`shepherd-core` is designed as a library and bundles data-models and file-access-routines for the shepherd-testbed, that are used by several codebases.

For postprocessing shepherds .h5-files usage of [shepherd_data](https://pypi.org/project/shepherd_data) is recommended.

## Features

- read and write shepherds hdf5-files
- create, read, write and convert experiments for the testbed
  - all required data-models are included
- simulate the virtual source, including virtual harvesters (and virtual converter as a whole)
- connect and query the testbed via a webclient (TestbedClient in alpha-stage)
  - offline usage defaults to static demo-fixtures loaded from yaml-files in the model-directories
- work with target-firmwares
  - embed, modify, verify, convert
  - **Note**: working with ELF-files requires external dependencies, see ``Installation``-Chapter
- decode waveforms (gpio-state & timestamp) to UART
- create an inventory (for deployed versions of software, hardware)

See [official documentation](https://orgua.github.io/shepherd) or [example scripts](https://github.com/orgua/shepherd-datalib/tree/main/shepherd_core/examples) for more details and usage. Most functionality is showcased in both. The [extra](https://github.com/orgua/shepherd-datalib/tree/main/shepherd_core/extra)-directory holds data-generators relevant for the testbed. Notably is a [trafficbench](https://github.com/orgua/TrafficBench)-experiment that's used to derive the link-matrix of the testbed-nodes.

## Config-Models in Detail

These pydantic data-models are used throughout all shepherd interfaces. Users can create an experiment, include their own content and feed it to the testbed.

- orchestration ``/data-models`` with focus on remote shepherd-testbed
- classes of sub-models
  - ``/base``: base-classes, configuration and -functionality for all models
  - ``/testbed``: meta-data representation of all testbed-components
  - ``/content``: reusable user-defined meta-data for fw, h5 and vsrc-definitions
  - ``/experiment``: configuration-models including sub-systems
  - ``/task``: digestible configs for shepherd-herd or -sheep
  - behavior controlled by ``ShpModel`` and ``content``-model
- a basic database is available as fixtures through a ``tb_client``
  - fixtures selectable by name & ID
  - fixtures support inheritance
- the models support
  - auto-completion with neutral / sensible values
  - complex and custom datatypes (i.e. PositiveInt, lists-checks on length)
  - checking of inputs and type-casting
  - generate their own schema (for web-forms)
  - pre-validation
  - store to & load from yaml with typecheck through wrapper
  - documentation
- experiment-definition is designed securely
  - types are limited in size (str)
  - exposes no internal paths
- experiments can be transformed to task-sets (``TestbedTasks.from_xp()``)

## Compatibility

| OS      | PyVersion  | Comment                                    |
|---------|------------|--------------------------------------------|
| Ubuntu  | 3.8 - 3.13 |                                            |
| Windows | 3.8 - 3.13 | no support for elf and hex-conversions yet |
| MacOS   | 3.8 - 3.13 | hex-conversion missing                     |

Notes:
- hex-conversion needs a working and accessible objcopy
- elf-supports needs
  - ``shepherd-core[elf]`` installs ``pwntools-elf-only``
  - most elf-features also still utilize hex-conversion

## Installation

The Library is available via PyPI and can be installed with

```shell
pip install shepherd-core -U

# or for the full experience (includes core)
pip install shepherd-data -U
```

For bleeding-edge-features or dev-work it is possible to install directly from GitHub-Sources (here `dev`-branch):

```Shell
pip install git+https://github.com/orgua/shepherd-datalib.git@dev#subdirectory=shepherd_core -U
# and on sheep with newer debian
sudo pip install git+https://github.com/orgua/shepherd-datalib.git@dev#subdirectory=shepherd_core -U --break-system-packages
```

If you are working with ``.elf``-files (embedding into experiments) you make "objcopy" accessible to python. In Ubuntu, you can either install ``build-essential`` or ``binutils-$ARCH`` with arch being ``msp430`` or ``arm-none-eabi`` for the nRF52.

```shell
sudo apt install build-essential
```

For more advanced work with ``.elf``-files (modify value of symbols / target-ID) you should install

```shell
pip install shepherd-core[elf]
```

and also make sure the prereqs for the [pwntools](https://docs.pwntools.com/en/stable/install.html) are met.

For creating an inventory of the host-system you should install

```shell
pip install shepherd-core[inventory]
```

## Unittests

To run the testbench, follow these steps:

1. Navigate your host-shell into the package-folder and
2. install dependencies
3. run the testbench (~ 320 tests):

```Shell
cd shepherd-datalib/shepherd_core
pip3 install ./[tests]
pytest
```
