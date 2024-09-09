"""Simulate behavior of virtual source algorithms.

The simulation recreates an observer-cape, the virtual Source and a virtual target
- input = hdf5-file with a harvest-recording
- output = optional as hdf5-file

The output file can be analyzed and plotted with shepherds tool suite.
"""

from contextlib import ExitStack
from pathlib import Path
from typing import Optional

import numpy as np
from tqdm import tqdm

from .. import CalibrationEmulator
from .. import Reader
from .. import Writer
from ..data_models import VirtualSourceConfig
from ..logger import logger
from . import VirtualSourceModel
from .target_model import TargetABC


def simulate_source(
    config: VirtualSourceConfig,
    target: TargetABC,
    path_input: Path,
    path_output: Optional[Path] = None,
    *,
    monitor_internals: bool = False,
) -> float:
    """Simulate behavior of virtual source algorithms.

    FN returns the consumed energy of the target.
    """
    stack = ExitStack()
    file_inp = Reader(path_input, verbose=False)
    stack.enter_context(file_inp)
    cal_emu = CalibrationEmulator()
    cal_inp = file_inp.get_calibration_data()

    if path_output:
        file_out = Writer(
            path_output, cal_data=cal_emu, mode="emulator", verbose=False, force_overwrite=True
        )
        stack.enter_context(file_out)
        file_out.store_hostname("emu_sim_" + config.name)
        file_out.store_config(config.model_dump())
        cal_out = file_out.get_calibration_data()

    src = VirtualSourceModel(
        config,
        cal_emu,
        dtype_in=file_inp.get_datatype(),
        log_intermediate=False,
        window_size=file_inp.get_window_samples(),
    )
    i_out_nA = 0
    e_out_Ws = 0.0
    if monitor_internals and path_output:
        stats_sample = 0
        stats_internal = np.empty((round(file_inp.runtime_s * file_inp.samplerate_sps), 11))
        try:
            # keep dependencies low
            from matplotlib import pyplot as plt
        except ImportError:
            logger.warning("Matplotlib not installed, plotting of internals disabled")
            stats_internal = None
    else:
        stats_internal = None

    for _t, v_inp, i_inp in tqdm(
        file_inp.read_buffers(is_raw=True), total=file_inp.buffers_n, desc="Buffers", leave=False
    ):
        v_uV = 1e6 * cal_inp.voltage.raw_to_si(v_inp)
        i_nA = 1e9 * cal_inp.current.raw_to_si(i_inp)

        for _n in range(len(_t)):
            v_uV[_n] = src.iterate_sampling(
                V_inp_uV=int(v_uV[_n]),
                I_inp_nA=int(i_nA[_n]),
                I_out_nA=i_out_nA,
            )
            i_out_nA = target.step(int(v_uV[_n]), pwr_good=src.cnv.get_power_good())
            i_nA[_n] = i_out_nA

            if stats_internal is not None:
                stats_internal[stats_sample] = [
                    _t[_n] * 1e-9,  # s
                    src.hrv.voltage_hold * 1e-6,
                    src.cnv.V_input_request_uV * 1e-6,  # V
                    src.hrv.voltage_set_uV * 1e-6,
                    src.cnv.V_mid_uV * 1e-6,
                    src.hrv.current_hold * 1e-6,  # mA
                    src.hrv.current_delta * 1e-6,
                    i_out_nA * 1e-6,
                    src.cnv.P_inp_fW * 1e-12,  # mW
                    src.cnv.P_out_fW * 1e-12,
                    src.cnv.get_power_good(),
                ]
                stats_sample += 1

        e_out_Ws += (v_uV * i_nA).sum() * 1e-15 * file_inp.sample_interval_s
        if path_output:
            v_out = cal_out.voltage.si_to_raw(1e-6 * v_uV)
            i_out = cal_out.current.si_to_raw(1e-9 * i_nA)
            file_out.append_iv_data_raw(_t, v_out, i_out)

    stack.close()

    if stats_internal is not None:
        stats_internal = stats_internal[:stats_sample, :]
        fig, axs = plt.subplots(4, 1, sharex="all", figsize=(20, 4 * 6), layout="tight")
        fig.suptitle(f"VSrc-Sim with {config.name}, Inp={path_input.name}, E={e_out_Ws} Ws")
        axs[0].set_ylabel("Voltages [V]")
        axs[0].plot(stats_internal[:, 0], stats_internal[:, 1:5])
        axs[0].legend(["V_cv_hold", "V_inp_Req", "V_cv_set", "V_cap"], loc="upper right")

        axs[1].set_ylabel("Current [mA]")
        axs[1].plot(stats_internal[:, 0], stats_internal[:, 5:8])
        axs[1].legend(["C_cv_hold", "C_cv_delta", "C_out"], loc="upper right")

        axs[2].set_ylabel("Power [mW]")
        axs[2].plot(stats_internal[:, 0:1], stats_internal[:, 8:10])
        axs[2].legend(["P_inp", "P_out"], loc="upper right")

        axs[3].set_ylabel("PwrGood [n]")
        axs[3].plot(stats_internal[:, 0], stats_internal[:, 10])
        axs[3].legend(["PwrGood"], loc="upper right")

        axs[3].set_xlabel("Runtime [s]")

        for ax in axs:
            # deactivates offset-creation for ax-ticks
            ax.get_yaxis().get_major_formatter().set_useOffset(False)
            ax.get_xaxis().get_major_formatter().set_useOffset(False)

        plt.savefig(path_output.with_suffix(".png"))
        plt.close(fig)
        plt.clf()

    return e_out_Ws
