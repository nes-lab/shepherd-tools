"""
CLI utility to convert Shepherd V1 energy environments to Shepherd Nova's format.

Requires start and end timestamps to cut the original eenv.
Ensures that the data has continuous timesteps for all sheep.
"""

import math
from pathlib import Path

import click
import h5py
import numpy as np
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models.base.calibration import CalibrationPair
from shepherd_core.data_models.base.calibration import CalibrationSeries
from shepherd_core.data_models.task import Compression
from shepherd_core.logger import log
from tqdm import trange

from shepherd_core import Writer as ShepherdWriter

SHP_V1_STEP_WIDTH: int = 10_000  # 10 us

WRITE_CHUNK_WIDTH: int = 10_000 * SHP_V1_STEP_WIDTH  # 10_000 x 10 us -> 0.1 s
PROCESS_CHUNK_SIZE: int = 1_000_000


def convert_file(in_file: Path, out_file: Path, tstart_ns: int, duration_ns: int) -> None:
    """
    Convert a Shepherd V1 input file to a Shepherd Nova output file.

    Only uses values within the specified time range.
    Ensures that the data has continuous timesteps.
    """
    log.info(f"Converting {in_file} -> {out_file}")

    if tstart_ns % SHP_V1_STEP_WIDTH != 0:
        msg = f"tstart not divisible by ShpV1's step width: {SHP_V1_STEP_WIDTH}"
        raise RuntimeError(msg)
    if duration_ns % WRITE_CHUNK_WIDTH != 0:
        msg = f"duration not divisible by write chunk width: {WRITE_CHUNK_WIDTH}"
        raise RuntimeError(msg)

    with h5py.File(in_file, "r") as input_h5:
        times = input_h5["data"]["time"]
        count = times.shape[0]
        in_chunk_count = math.ceil(count / PROCESS_CHUNK_SIZE)

        # Find index for tstart in the input file
        pot_start_idxs = []
        for chunk_idx in trange(in_chunk_count, desc="Scanning chunks for start timestamp"):
            chunk_start_idx = chunk_idx * PROCESS_CHUNK_SIZE
            chunk_end_idx = chunk_start_idx + PROCESS_CHUNK_SIZE
            chunk = times[chunk_start_idx:chunk_end_idx]

            pot_start_idxs.extend(list(chunk_start_idx + np.where(chunk == tstart_ns)[0]))

        if len(pot_start_idxs) != 1:
            msg = f"tstart is not unique (occurs {len(pot_start_idxs)} times) in file {in_file!s}"
            raise RuntimeError(msg)
        start_idx = int(pot_start_idxs[0])

        # Calculate end index and process chunk count
        steps = duration_ns // SHP_V1_STEP_WIDTH
        end_idx = start_idx + steps
        process_chunk_count = math.ceil(steps / PROCESS_CHUNK_SIZE)

        voltages = input_h5["data"]["voltage"]
        v_gain = voltages.attrs["gain"]
        v_offset = voltages.attrs["offset"]

        currents = input_h5["data"]["current"]
        c_gain = currents.attrs["gain"]
        c_offset = currents.attrs["offset"]

        # Calculate minimum values to ensure voltage and current values are non-negative
        v_min = math.ceil(0 - v_offset / v_gain)
        c_min = math.ceil(0 - c_offset / c_gain)

        with ShepherdWriter(
            file_path=out_file,
            compression=Compression.gzip1,
            mode="harvester",
            datatype=EnergyDType.ivtrace,  # IV-trace
            window_samples=0,  # 0 since dt is IV-trace
            cal_data=CalibrationSeries(
                # match voltage/current calibration from original file
                voltage=CalibrationPair(
                    gain=voltages.attrs["gain"], offset=voltages.attrs["offset"]
                ),
                current=CalibrationPair(
                    gain=currents.attrs["gain"], offset=currents.attrs["offset"]
                ),
            ),
            verbose=False,
        ) as writer:
            writer.store_hostname(out_file.stem)

            # Stream data over
            for chunk_idx in trange(process_chunk_count, desc="Converting chunks"):
                chunk_start_idx = start_idx + chunk_idx * PROCESS_CHUNK_SIZE
                chunk_end_idx = min(chunk_start_idx + PROCESS_CHUNK_SIZE, end_idx)

                # Get chunk data
                ts = times[chunk_start_idx:chunk_end_idx]
                vs = voltages[chunk_start_idx:chunk_end_idx]
                cs = currents[chunk_start_idx:chunk_end_idx]

                if (
                    len(ts) != chunk_end_idx - chunk_start_idx
                    or len(vs) != chunk_end_idx - chunk_start_idx
                    or len(cs) != chunk_end_idx - chunk_start_idx
                ):
                    raise RuntimeError("Input file has insufficient data")

                # Clip voltage and current data
                vs = np.clip(vs, a_min=v_min, a_max=None)
                cs = np.clip(cs, a_min=c_min, a_max=None)

                # Ensure time steps are really continuous
                dts = ts[1:] - ts[: len(ts) - 1]
                if not np.all(dts == SHP_V1_STEP_WIDTH):
                    raise RuntimeError("Unexpected non-standard timestep encountered")

                # Write chunk data
                writer.append_iv_data_raw(ts, vs, cs)
    log.info(
        "\t-> finished with size-reduction to "
        f"{100 * out_file.stat().st_size / in_file.stat().st_size:.2f} %"
    )


def convert(input_files: list[Path], output_dir: Path, start_ns: int, duration_ns: int) -> None:
    """
    Convert specified Shepherd V1 input files to a Shepherd Nova energy environment.

    Only the specified time range (corresponding to system time values from the
    input files) is considered.
    """
    output_dir.mkdir(exist_ok=True)
    for i, input_file in enumerate(input_files):
        output_file = output_dir / f"node{i}.h5"
        if output_file.exists():
            log.warning(
                f"Output file {output_file} exists. Skipping corresponding input file {input_file}"
            )
            continue

        convert_file(
            in_file=input_file, out_file=output_file, tstart_ns=start_ns, duration_ns=duration_ns
        )


@click.command(short_help="Convert ShpV1 eenv to Shepherd Nova's format")
@click.argument(
    "INPUT_FILES",
    type=click.Path(exists=True, resolve_path=True, file_okay=True, dir_okay=False, path_type=Path),
    nargs=-1,
    required=True,
)
@click.option(
    "-o",
    "--output-directory",
    type=click.Path(resolve_path=True, path_type=Path),
    required=True,
    help="Output file to which the scan report will be written",
)
@click.option(
    "-s", "--start-ns", type=int, required=True, help="Start timestamp (system time in ns)"
)
@click.option("-d", "--duration-ns", type=int, required=True, help="Duration (in ns)")
def cli(input_files: list[Path], output_dir: Path, start_ns: int, duration_ns: int) -> None:
    """CLI Entrypoint."""
    convert(
        input_files=input_files, output_dir=output_dir, start_ns=start_ns, duration_ns=duration_ns
    )


if __name__ == "__main__":
    cli()
