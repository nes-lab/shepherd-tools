## Shepherd - Datalib

### Installation

manual:

- clone repository
- navigate shell into directory
- call `python setup.py install`

via pip (TODO):

`pip3 install shepherd_data`

### Info about the programming interface

basic usage (recommendation):

```
import shepherd_data as shpd

with shpd.Reader("./hrv_sawtooth_1h.h5") as db:
    print(f"Mode: {db.get_mode()}")
    print(f"Window: {db.get_window_samples()}")
    print(f"Config: {db.get_config()}")
```

available functionality:

- `Reader()`
  - file can be checked for plausibility and validity (`is_valid()`)
  - internal structure of h5file (`get_metadata()` or `save_metadata()` ... to yaml) with lots of additional data
  - access data and various converters, calculators
    - `read_buffers()` -> generator that provides one buffer per call, can be configured on first call 
    - `get_calibration_data()`
    - `get_windows_samples()`
    - `get_mode()`
    - `get_config()`
    - direct access to root h5-structure via `reader['element']`
    - converters for raw / physical units: `si_to_raw()` & `raw_to_si()`
    - `energy()` sums up recorded power over time
  - `downsample()` (if needed) visualize recording (`plot_to_file()`)
- `Writer()`
  - inherits all functionality from Reader
  - `append_iv_data_raw()`
  - `append_iv_data_si()`
  - `set_config()`
  - `set_windows_samples()`
- IVonne Reader
  - `convert_2_ivcurves()` converts ivonne-recording into a shepherd ivcurve
- examples
  - `example_generate_sawtooth.py` is using Writer to generate a 60s ramp with 1h repetition and uses Reader to dump metadata of that file
  - `example_extract_logs.py` is analyzing all files in directory, saves logging-data and calculates cpu-load and data-rate
  - `example_convert_ivonne.py` converts IVonne recording (`jogging_10m.iv`) to shepherd ivcurves, NOTE: slow implementation 
  - `example_plot_traces.py` demos some mpl-plots with various zoom levels
  - `jogging_10m.iv`
      - 50 Hz measurement with Short-Circuit-Current and two other parameters
      - recorded with "IVonne"

### Info about the cli interface

TODO

### Compression & Beaglebone

- supported are uncompressed, lzf and gzip with level 1 (order of recommendation)
  - lzf seems better-suited due to lower load, or if space isn't a constraint: uncompressed (None as argument)
  - note: lzf seems to cause trouble with some third party hdf5-tools
  - compression is a heavy load for the beaglebone, but it got more performant with recent python-versions
- size-experiment A: 24 h of ramping / sawtooth (data is repetitive with 1 minute ramp) 
  - gzip-1: 49'646 MiB -> 588 KiB/s
  - lzf: 106'445 MiB -> 1262 KiB/s
  - uncompressed: 131'928 MiB -> 1564 KiB/s
- cpu-load-experiments (input is 24h sawtooth, python 3.10 with most recent libs as of 2022-04)
  - warning: gpio-traffic and other logging-data can cause lots of load

```
  emu_120s_gz1_to_gz1.h5 	-> emulator, cpu_util [%] = 65.59, data-rate =  352.0 KiB/s
  emu_120s_gz1_to_lzf.h5 	-> emulator, cpu_util [%] = 57.37, data-rate =  686.0 KiB/s
  emu_120s_gz1_to_unc.h5 	-> emulator, cpu_util [%] = 53.63, data-rate = 1564.0 KiB/s
  emu_120s_lzf_to_gz1.h5 	-> emulator, cpu_util [%] = 63.18, data-rate =  352.0 KiB/s
  emu_120s_lzf_to_lzf.h5 	-> emulator, cpu_util [%] = 58.60, data-rate =  686.0 KiB/s
  emu_120s_lzf_to_unc.h5 	-> emulator, cpu_util [%] = 55.75, data-rate = 1564.0 KiB/s
  emu_120s_unc_to_gz1.h5 	-> emulator, cpu_util [%] = 63.84, data-rate =  351.0 KiB/s
  emu_120s_unc_to_lzf.h5 	-> emulator, cpu_util [%] = 57.28, data-rate =  686.0 KiB/s
  emu_120s_unc_to_unc.h5 	-> emulator, cpu_util [%] = 51.69, data-rate = 1564.0 KiB/s 
```

### Open Tasks

- implementations for this lib
  - plotting for multi-node
  - plotting more generalized (power, cpu-util, ..., own directory)
  - some metadata is wrong (non-scalar datasets)
  - tests
- main shepherd-code
  - proper validation first
  - update commentary
  - pin-description should be in yaml (and other descriptions for cpu, io, ...)
  - datatype-hint in h5-file (ivcurve, ivsample, isc_voc)
  - hostname for emulation
  - full and minimal config into h5

### Old Scripts and Files:
- `gen_data.py` creates hdf-files for every type of database we want to support.
    - `curve2trace()`
      - get voltage/current-trace by sending curve through MPPT-Converter or other Optimizer/Tracker (in `mppt.py`)
      - can take very long (especially MPPT), but output can be limited by `duration` variable
- `iv_reconstruct.py` ~~shows how the transformation-coefficients work~~ -> NOT UP TO DATE
- `mppt.py` contains converters / trackers for `gen_data`
- `plot.py`
    - `python plot.py db_traces.h5` plots the content of the hdf
