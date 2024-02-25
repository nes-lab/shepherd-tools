# Content Generators

These scripts are used to fill the database of the testbed-server. Currently, they can:

- generate energy environments and their models
- generate embedded firmware-models from [another repo](https://github.com/orgua/shepherd-targets)
- use data-models as fixtures for core-lib
- create reoccurring experiments / tasks
  - taking the RF-survey to derive a link-matrix
  - testing each MCU on the target-PCBs before deployment

Currently, this is a pseudo-database inside the core-lib.
When core-models are changed rerun all scripts here. Begin with all `gen_*` and end with `prime_database` and `reset fixtures`.
