"""script will:
- generate static environments
- saves energy-env to yaml
"""

from itertools import product
from pathlib import Path

import numpy as np
from tqdm import trange

from shepherd_core import Reader as ShpReader
from shepherd_core import Writer as ShpWriter
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models import EnergyEnvironment
from shepherd_core.logger import logger

if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()
    if Path("/var/shepherd/").exists():
        path_eenv = Path("/var/shepherd/content/eenv/nes_lab/")
    else:
        path_eenv = path_here / "content/eenv/nes_lab/"
    # Config
    voltages_V = [3.0, 2.0]
    currents_A = [50e-3, 10e-3, 5e-3, 1e-3]
    duration_s = 60
    repetitions = 60

    if not path_eenv.exists():
        path_eenv.mkdir(parents=True)

    for _v, _c in product(voltages_V, currents_A):
        v_str = f"{round(_v * 1000)}mV"
        c_str = f"{round(_c * 1000)}mA"
        t_str = f"{round(duration_s * repetitions)}s"
        name = f"eenv_static_{v_str}_{c_str}_{t_str}"
        file_path = path_eenv / f"{name}.h5"

        if file_path.exists():
            logger.info("File exists, will skip: %s", file_path.name)
        else:
            with ShpWriter(file_path) as file:
                file.store_hostname("artificial")
                # values in SI units
                timestamp_vector = np.arange(0.0, duration_s, file.sample_interval_ns / 1e9)
                voltage_vector = np.linspace(_v, _v, int(file.samplerate_sps * duration_s))
                current_vector = np.linspace(_c, _c, int(file.samplerate_sps * duration_s))

                for idx in trange(repetitions, desc="generate"):
                    timestamps = idx * duration_s + timestamp_vector
                    file.append_iv_data_si(timestamps, voltage_vector, current_vector)

        meta_path = file_path.with_suffix(".yaml")
        if meta_path.exists():
            logger.info("File exists, will skip generation of: %s", meta_path.name)
        else:
            with ShpReader(file_path) as file:
                energy = file.energy()

            EnergyEnvironment(
                name=name,
                description=f"Artificial static Energy Environment, {v_str}, {c_str}, {t_str}",
                data_path=file_path.absolute().as_posix(),
                data_type=EnergyDType.ivsample,
                duration=duration_s * repetitions,
                energy_Ws=energy,
                valid=True,
                indoor=True,
                location="Lab-VSrc",
                owner="Ingmar",
                group="NES_Lab",
                visible2group=True,
                visible2all=True,
            ).to_file(meta_path, minimal=False)
