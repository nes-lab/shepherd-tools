import math
import time
import numpy as np
from pathlib import Path
from tqdm import trange

from shepherd_core import Writer as ShepherdWriter
from shepherd_core.data_models.base.calibration import CalibrationPair, CalibrationSeries
from shepherd_core.commons import SAMPLERATE_SPS_DEFAULT
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models.task import Compression

STEP_WIDTH = 1.0 / SAMPLERATE_SPS_DEFAULT # 10 us
IDEAL_VOLTAGE_GAIN = 1e-6 # PRU uses uV
IDEAL_CURRENT_GAIN = 1e-9 # PRU uses nA

def _gen_ideal_calibration_series():
    # Generate calibration series using ideal voltage and current gain
    return CalibrationSeries(voltage=CalibrationPair(gain=IDEAL_VOLTAGE_GAIN, offset=0),
                             current=CalibrationPair(gain=IDEAL_CURRENT_GAIN, offset=0))

def gen_ivtrace_writer(file_path):
    return ShepherdWriter(file_path=file_path,
                   compression=Compression.gzip1,
                   mode='harvester',
                   datatype=EnergyDType.ivsample, # IV-trace
                   window_samples=0, # 0 since dt is IV-trace
                   cal_data = _gen_ideal_calibration_series())


class EEnvGenerator:
    def __init__(self, node_count, seed):
        self.node_count = node_count
        self.rnd_gen = np.random.Generator(bit_generator=np.random.PCG64(seed))

    def generate_iv_pairs(self, count):
        raise RuntimeError("this is an abstract class")

def generate_h5_files(output_dir: Path, duration: float, chunk_size: int, generator: EEnvGenerator):
    chunk_duration = chunk_size * STEP_WIDTH
    chunk_count = math.ceil(duration / chunk_duration)

    # Prepare datafiles
    files = [gen_ivtrace_writer(file_path=output_dir / f'sheep{i}.h5') for i in range(generator.node_count)]
    for (i, file) in enumerate(files):
        file.store_hostname(f'sheep{i}.h5')

    times_per_chunk = np.arange(0, chunk_size) * STEP_WIDTH

    print('Generating energy environment...')
    start_time = time.time()
    for i in trange(chunk_count, desc="Generating chunk: ", leave=False):
        times_unfiltered = chunk_duration * i + times_per_chunk
        times = times_unfiltered[np.where(times_unfiltered <= duration)]
        count = len(times)

        iv_pairs = generator.generate_iv_pairs(count=count)

        for (file, (voltages, currents)) in zip(files, iv_pairs):
            file.append_iv_data_si(times, voltages, currents)
    end_time = time.time()
    print(f'Done! Generation took {end_time - start_time}')

    for file in files:
        # TODO Reader has no .close()
        file.h5file.close()
