# Shepherd - Datalib

[![PyPiVersion](https://img.shields.io/pypi/v/shepherd_data.svg)](https://pypi.org/project/shepherd_data)
[![Pytest](https://github.com/orgua/shepherd-datalib/actions/workflows/python-app.yml/badge.svg)](https://github.com/orgua/shepherd-datalib/actions/workflows/python-app.yml)
[![CodeStyle](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Main Project**: [https://github.com/orgua/shepherd](https://github.com/orgua/shepherd)

**Source Code**: [https://github.com/orgua/shepherd-datalib](https://github.com/orgua/shepherd-datalib)

---

The Repository contains python packages for the [shepherd](https://github.com/orgua/shepherd)-testbed

- `/shepherd_core` bundles functionality that is used by multiple tools
- `/shepherd_data` holds the data-module that is designed for users of the testbed

## Development

### PipEnv

- clone repository
- navigate shell into directory
- install environment
- activate shell
- optional
  - update pipenv (optional)
  - add special packages with `-dev` switch

```Shell
git clone https://github.com/orgua/shepherd-datalib
cd .\shepherd-datalib

pipenv install --dev
pipenv shell

pipenv update
pipenv install --dev pytest
```

### Update dynamic Fixtures

When external dependencies ([Target-Lib](https://github.com/orgua/shepherd-targets/)) change, the fixtures should be updated.

```shell
python3 extra/gen_firmwares.py
python3 extra/gen_energy_envs.py
python3 extra/prime_database.py
# commit the updated 'shepherd_core/shepherd_core/data_models/content/_external_fixtures.yaml'
# delete (optional) 'extra/content'
```

### Running Testbench

- run pytest in ``_core``- or ``_data``-subdirectory
- alternative (below) is running from failed test to next fail

```shell
pytest
pytest --stepwise
```

### code coverage (with pytest)

- run coverage in ``_core``- or ``_data``-subdirectory
- check results (in browser `./htmlcov/index.html`)

```shell
coverage run -m pytest

coverage html
# or simpler
coverage report
```

## Release-Procedure

- increase version number in ``__init__.py`` of both packages
- install and run ``pre-commit`` for QA-Checks, see steps below
- run unittests from both packages locally
  - additionally every commit gets automatically tested by GitHub workflows
- update changelog in ``HISTORY.md``
- move code from dev-branch to main by PR
- add tag to commit - reflecting current version number - i.e. ``v23.9.0``
- GitHub automatically creates a release & pushes the release to pypi
- update release-text with latest Changelog
- rebase dev-branch

```shell
pip3 install pre-commit
# or better
pipenv shell

pre-commit run --all-files

# additional QA-Tests (currently with open issues)
pyright
ruff check .

# inside sub-modules unittests
cd shepherd_core
pytest --stepwise
# when developers add code they should make sure its covered by the testsuite
coverage run -m pytest
coverage html
```

## Open Tasks

- [click progressbar](https://click.palletsprojects.com/en/8.1.x/api/#click.progressbar) -> could replace tqdm
- implementations for this lib
  - generalize up- and down-sampling, use out_sample_rate instead of ds-factor
    - lib samplerate (tested) -> promising, but designed for float32 and range of +-1.0
    - lib resampy (tested) -> could be problematic with slice-iterator
    - https://stackoverflow.com/questions/29085268/resample-a-numpy-array
    - scipy.signal.resample, https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample.html
    - scipy.signal.decimate, https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.decimate.html
    - scipy.signal.resample_poly, https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample_poly.html#scipy.signal.resample_poly
    - timestamps could be regenerated with np.arange( tmin, tmax, 1e9/samplerate)
  - generalize converters (currently in IVonne)
    - isc&voc <-> ivcurve
    - ivcurve -> ivsample
  - plotting and downsampling for IVCurves ()
  - plotting more generalized (power, cpu-util, ..., if IV then offer power as well)
  - some metadata is calculated wrong (non-scalar datasets)
  - unittests & codecoverage -> 79% with v22.5.4, https://pytest-cov.readthedocs.io/en/latest/config.html
    - test example: https://github.com/kvas-it/pytest-console-scripts
    - use coverage to test some edge-cases
  - sub-divide valid() into healthy()
  - add gain/factor to time, with repair-code
  - add https://pypi.org/project/nessie-recorder/#files
- main shepherd-code
  - proper validation first
  - update commentary
  - pin-description should be in yaml (and other descriptions for cpu, io, ...)
  - datatype-hint in h5-file (ivcurve, ivsample, isc_voc), add mechanism to prevent misuse
  - hostname for emulation
  - full and minimal config into h5
  - use the datalib as a base
  - isc-voc-harvesting
  - directly process isc-voc -> resample to ivcurve?
