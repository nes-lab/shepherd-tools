# Shepherd-Data-Tool

[![PyPiVersion](https://img.shields.io/pypi/v/shepherd_data.svg)](https://pypi.org/project/shepherd_data)
[![image](https://img.shields.io/pypi/pyversions/shepherd_data.svg)](https://pypi.python.org/pypi/shepherd-data)
[![Pytest](https://github.com/orgua/shepherd-datalib/actions/workflows/py_unittest.yml/badge.svg)](https://github.com/orgua/shepherd-datalib/actions/workflows/py_unittest.yml)
[![CodeStyle](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Main Documentation**: <https://orgua.github.io/shepherd>

**Source Code**: <https://github.com/orgua/shepherd-datalib>

**Main Project**: <https://github.com/orgua/shepherd>

---

`shepherd-data` eases the handling of hdf5-recordings used by the [shepherd](https://github.com/orgua/shepherd)-testbed. Users can read, validate and create files and also extract, down-sample and plot information.

## Installation

### PIP - Online

```shell
pip3 install shepherd-data -U
```

For bleeding-edge-features or dev-work it is possible to install directly from GitHub-Sources (here `dev`-branch):

```Shell
pip install git+https://github.com/orgua/shepherd-datalib.git@dev#subdirectory=shepherd_data -U
```

## More

Please consult the [official documentation](https://orgua.github.io/shepherd) for more, it covers:

- general context
- command-line interface
- programming interface
