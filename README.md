# Shepherd - Data

[![PyPiVersion](https://img.shields.io/pypi/v/shepherd_data.svg)](https://pypi.org/project/shepherd_data)
[![Pytest](https://github.com/orgua/shepherd-datalib/actions/workflows/python-app.yml/badge.svg)](https://github.com/orgua/shepherd-datalib/actions/workflows/python-app.yml)
[![CodeStyle](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

This Repo contains python packages for the [shepherd](https://github.com/orgua/shepherd)-testbed

- `/shepherd_core` bundles functionality that is used by multiple tools
- `/shepherd_data` holds the datalib that is designed for users of the testbed

---

**Main Project**: [https://github.com/orgua/shepherd](https://github.com/orgua/shepherd)

**Source Code**: [https://github.com/orgua/shepherd-datalib](https://github.com/orgua/shepherd-datalib)

# Installation

## PIP - Online from PyPI

The Library is available via PyPI and can be installed with

```shell
  pip install shepherd-core -U
  pip install shepherd-data -U
  # NOTE: -data installs -core automatically
```

## PIP - Online from GitHub

For install directly from GitHub-Sources (here `dev`-branch):

```Shell
pip install git+https://github.com/orgua/shepherd-datalib.git@dev#subdirectory=shepherd_core -U
pip install git+https://github.com/orgua/shepherd-datalib.git@dev#subdirectory=shepherd_data -U
```

**Advantage**: test unreleased version, skip manual cloning


## Release-Procedure

- increase version number in __init__.py of both packages
- install and run pre-commit for QA-Checks, see steps below
- every commit get automatically tested by GitHub
- put together a release on GitHub - the tag should match current version-number
- GitHub automatically pushes the release to pypi


```shell
pip3 install pre-commit

pre-commit run --all-files

# additional QA-Tests (currently with open issues)
pyright
ruff check .

# inside sub-modules unittests
cd shepherd_core
pytest
# when developers add code they should make sure its covered by testsuite
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
