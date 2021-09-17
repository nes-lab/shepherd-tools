## Shepherd - Datalib

### Info about Scripts and Files

- `gen_data.py` creates hdf-files for every type of database we want to support.
    - `gen_regvoltage()`
      - custom voltage-trace that gets handed to emulator (on/off-patter, constant-voltage, ...)
    - `gen_ivcurve()`
      - construct artificial proto-curve and calculate transformation-coefficients for every time-step
      - based on real data (`jogging_10m.iv`)
    - `curve2trace()`
      - get voltage/current-trace by sending curve through MPPT-Converter or other Optimizer/Tracker (in `mppt.py`)
      - can take very long (especially MPPT), but output can be limited by `duration` variable
- `iv_reconstruct.py` shows how the transformation-coefficients work
- `jogging_10m.iv`
    - 50 Hz measurement with Short-Circuit-Current and two other parameters
    - recorded with "IVonne"
- `mppt.py` contains converters / trackers for `gen_data`
- `plot.py`
    - `python plot.py db_traces.h5` plots the content of the hdf
