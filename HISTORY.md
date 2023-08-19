# History of Changes


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
  - TODO: switch to pydantic V2 (loading datamodels still dominant)

## v2023.08.5

- ELF-support by default

## v2023.08.4

- add and use fw-helper-fn: compare_hash(), base64_to_hash()
- allow to generate fw-mod from fw-model
- cleanup import-system for pwntools (dependencies caused trouble on windows & BBone)

## v2023.08.3

- improve handling of uninstalled sub-modules (elf, inventory)
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
