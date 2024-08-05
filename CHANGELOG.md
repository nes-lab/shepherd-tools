# History of Changes

## v2024.8.1

- plotting: disable creation of tick-offset 
- cal: add si-unit
- add `core/example/vsource_emulation.py` that processes hdf5-recordings and also generates them 
- virtual source model
  - fix off-by-1 error in rows of efficiency-LUTs
  - remove limiting-behavior of boost-regulator
  - add residue-feature to calibration-converters
  - bq25504 - to not cut-off output

## v2024.7.4

- fix two bugs in calibration
- plotting
  - re-enable plotting of ivcurves (but still warn about it)
  - add plot for power (IV combined)
  - add option to only plot power
  - switch from uA & uW to mA & mW for plots

## v2024.7.3

- fixture-cache -> limit usage to sheep / bbone
- include lib-version in experiment- and wrapper-data
- tb-client - improve query of data
- create AbstractBaseClass for tb-client to allow dedicated Clients like `FixturesClient`, `WebClient`, `DbClient`
- `extra/gen_firmwares.py` shows size of different firmwares (elf, hex, embedded-yaml, embedded-json)
  - yaml / json does embed elf with zstd-compression level20 and base64-encoding

```
saved FW ./content/fw/nes_lab/nrf52_rf_test/build.elf
 -> size-stat: {'elf': 860904, 'hex': 4340, 'yaml': 232007, 'json': 231932}
saved FW ./content/fw/nes_lab/nrf52_deep_sleep/build.elf
 -> size-stat: {'elf': 619088, 'hex': 799, 'yaml': 170395, 'json': 170320}
saved FW ./content/fw/nes_lab/nrf52_rf_survey/build.elf
 -> size-stat: {'elf': 799636, 'hex': 123517, 'yaml': 287927, 'json': 287852}
 ```

## v2024.7.2

- inventory - bugfix for beagle-info
- extract - more robust file-handling
- extract-uart - more robust waveform decoding
- extract-meta - more robust operation
- add script to generate plot of link-matrix

## v2024.7.1

- core - replace scipy-code with numpy to remove dependency
- inventory - add storage-stats and beagle-version-info
- ivonny - explain parameters, obfuscated shockley diode equation
- update deps & tooling

## v2024.5.1

- move config to root-level
- add newest log-names to meta-extractor
- fix advice in error-text
- update deps

## v2024.4.2

- fix import-bug regarding fixtures
- warn when fixtures are empty
- fix relative imports (be as specific as possible)
- fix lots of lint warnings
- improve documentation
- improve error-handling

## v2024.4.1

- add UUID to models
- improve docstrings to be used by shepherd-doc
- improved docs
- switch fully to pyproject.toml
- update deps
- (extra) testbed-layout-table: add fields
- represent current testbed-structure

## v2023.12.1

- optimize reader.read_buffers() to allow omitting timestamp (less overhead)
- change default compression to lzf
- weaken errors / warnings for missing timestamps
- toolchain: replace isort, black, flake8, pylint by ruff

## v2023.11.1

- warn about errors during test-run during validation (default when opening shepherd-files)
- update testbed-structure (changed positions, composition and added two nodes)
- extend GH-Actions (with unittests) to windows & macOS
- fix inventory

## v2023.10.3

- add warning-system for errors in log
- improve verbosity and messages

## v2023.10.2

- fix exit-fn
- allow checking presence of variables in model (if X in Y)
- more efficient coding
- cleanup try-import-code
- cleanup singletons

## v2023.10.1

- updated extraction of included data
- improved handling of faulty files
- supported python is now 3.8 - 3.12
- lots of linting, more pythonic style and interface-improvements
- add timezone to datetime-objects
- more explicit typing

## v2023.9.9

- lots of bugfix
- validate data vs data_type on firmware
- offer example for generic experiment definitions
- shepherd_data: also export stdout-log


## v2023.9.8

- new example and generators
- lots of small bugfixes

## v2023.9.7

- refine content-paths and path-handling of the testbed
- rework data-generators in '/extra'
- testbed-client - add ownership-data if none was provided
- observer-task now has optional start-time and the other models can react to that
- update content-fixtures
- file-based content now has a local-flag to show it has to be copied to the testbed
- discard older fixture-buffer (1 day)

## v2023.9.6

- fix workflows
- latest pydantic-update 2.4 brings some speed improvement for sheep (<10%)

## v2023.9.4

- update fixtures with real testbed-data
- refine testbed-models
  - objects with active=False can't be used in experiment
  - target.id is now used as selector and is also encouraged to be dynamic to shape the testbed (see layout-map in doc)
- integrate gpio-decoder into reader
  - .gpio_to_waveforms()
  - .gpio_to_uart()
- rework GitHub workflow to all release and publish by tagging a commit

## v2023.9.3

- uart-decoder: baudrate-detection more robust
- shpModel: change export to make sure set-parameters get exported
- generators: enable rec of uart
- refactor verbosity-system
- GitHubWorkflow refactoring
- add waveform-extraction for shepherd-data - cmd: extract-uart

## v2023.9.2

- breaking change: cores BaseReader and BaseWriter just become Reader & Writer

## v2023.09.0

- allow negative values when converting raw to SI-units
- lift restriction for pandas < v2
- update dependencies and fix incompats & warnings
- warn when files are not overwritten
- create data-generators for the testbed (./extra)
- improve file-handling
- bugfixes for task-handling
- update documentation
- update IPv4-representation
- extend model with more representation-types (yaml, str, dict, ...)

## v2023.08.8

- further fixes for datetimes
- make shpModel even more like a dict
- fix name-collisions
- add CapeData from Sheep
- extend User.active
- add output_paths to task-sets and make them compatible with prepare_tasks() & extract_tasks()

## v2023.08.7

- move to pydantic V2 with `bump-pydantic`
  - disadvantage 1: min-string-size for models had to be reduced from 4 to 1, due to different local overwriting-rules
  - disadvantage 2: its 60% slower on BBone

```Shell
sudo python3 -X importtime -c 'from shepherd_core.data_models.task import EmulationTask' 2> importtime.log
#  8.4 s on v2023.8.6, pydantic 1.10
# 13.9 s on v2023.8.7, pydantic 2.2.1, core 2.6.1
# 13.7 s with defer_build=True ⇾ triggers bug?
# 12.8 s on v2024.4.1, pydantic 2.7.0, core 2.18.1
# 10.3 s on v2024.5.1, pydantic 2.7.4, core 2.18.4 - debian 12.5
# 10.4 s on v2024.5.1, pydantic 2.8.0, core 2.20.0
```

## v2023.08.6

- add zstd-compression for embedded fw
- derive fw-name if not provided
- only mock uninstalled modules / packages
- speedup on BBone from 47 s to ~10 s
  - hash-default-value in user-model took 25 s
  - loading fixtures took 6 s (now pickled on first use)
  - scipy.stats takes 4.4 s to import in cal_measurement
  - requests takes 1.3 s to import in testbed_client
  - next slowest external module are: numpy 1.5 s, pwnlib.elf 1.4 s

## v2023.08.5

- ELF-support by default

## v2023.08.4

- add and use fw-helper-fn: compare_hash(), base64_to_hash()
- allow to generate fw-mod from fw-model
- cleanup import-system for pwntools (dependencies caused trouble on windows & BBone)

## v2023.08.3

- improve handling of uninstalled submodules (elf, inventory)
- add helper FNs for fw_tools, including utests
- fix missing imports
- add hash to fw-model

## v2023.08.2

- fix missing imports
- better handle uninstalled sub-modules

## v2023.08.1

- add inventory-functionality
- add uart-waveform decoder
- improve codequality & extend unittests
- update dependencies
- add this changelog
