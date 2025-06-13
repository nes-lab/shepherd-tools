"""Generators for Energy-Environments.

These energy environments are used for shepherd and are available on the testbed.
All scripts are reproducible, so users can create exact copies.
It is also possible to increase runtime and node-count for future extensions while
keeping the original timeframes identical.
The scripts offer

- static traces
- random on-off-pattern with fixed periodic window-length and duty cycle
- on-off-pattern with random on-duration and duty cycle

Future extensions:

- artificial solar trace - based on multivariant random walk
- artificial solar IV-surface
- reworked zenodo-traces, mentioned in paper

"""
