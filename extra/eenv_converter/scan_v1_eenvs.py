"""
CLI utility to scan Shepherd V1 energy environments.

Detects timeranges where all sheep have data with continuous
10 us timesteps and generates a report.
"""

import itertools
from pathlib import Path

import click
import h5py
import numpy as np
from pydantic import NonNegativeFloat
from pydantic import NonNegativeInt
from tqdm import trange

from shepherd_core import Reader as ShepherdReader
from shepherd_core.data_models.base.shepherd import ShpModel

SHP_V1_STEP_WIDTH = 10_000  # 10 us
SHP_V1_CHUNK_STEPS = 10_000  # 0.1 s chunks
SHP_V1_CHUNK_WIDTH = SHP_V1_STEP_WIDTH * SHP_V1_CHUNK_STEPS


class ScanReportProfile(ShpModel):
    """Data class to hold the scan report for a single profile (sheep)."""

    original_path: Path
    original_start: NonNegativeInt
    original_end: NonNegativeInt
    original_count: NonNegativeInt
    original_duration: NonNegativeFloat

    # Both ranges include start and end
    continuous_ranges_indices: list[tuple[NonNegativeInt, NonNegativeInt]]
    continuous_ranges_times: list[tuple[NonNegativeInt, NonNegativeInt]]


class CommonRange(ShpModel):
    """Data class to hold timeranges where all profiles have continuous data."""

    tstart: NonNegativeInt
    tend: NonNegativeInt
    duration: NonNegativeFloat
    # Includes start and end indices
    profile_range_indices: list[NonNegativeInt]


class ScanReport(ShpModel):
    """Data class to hold the output report."""

    profiles: list[ScanReportProfile]
    common_ranges: list[CommonRange]


def find_continuous_ranges(ds_time: h5py.Dataset, count: int) -> list[int]:
    """Find ranges (indices) with continuous 10 us timesteps in a time dataset."""
    if not count % SHP_V1_CHUNK_STEPS == 0:
        raise RuntimeError("count not divisible by chunk size")
    chunk_count = count // SHP_V1_CHUNK_STEPS

    range_start = 0
    continuous_ranges = []
    trailing_zeros = False

    for chunk_idx in trange(1, chunk_count, desc="Finding continuous time ranges"):
        sample_idx = chunk_idx * SHP_V1_CHUNK_STEPS
        now = ds_time[sample_idx]
        prev = ds_time[sample_idx - 1]

        if now == 0:
            # Time jumped to 0
            trailing_zeros = True
            continuous_ranges.append((range_start, sample_idx - 1))
            break

        # Convert to int to account for backwards timesteps (negative deltas)
        dt = int(now) - int(prev)

        if dt == 10000:
            # Standard timestep
            continue

        continuous_ranges.append((range_start, sample_idx - 1))
        range_start = sample_idx

    if trailing_zeros:
        # Ensure the recording actually ended
        for trailing_idx in range(chunk_idx, chunk_count):
            timestamps = ds_time[
                trailing_idx * SHP_V1_CHUNK_STEPS : (trailing_idx + 1) * SHP_V1_CHUNK_STEPS
            ]
            if not np.all(timestamps == 0):
                raise RuntimeError("Non-zero timestamp found after jump to zero")
    else:
        # Complete final range
        continuous_ranges.append((range_start, count - 1))

    return continuous_ranges


def find_common_ranges(time_ranges: list[list[tuple[int, int]]]) -> list[CommonRange]:
    """Find common continuous time ranges given individual ones."""
    common_ranges = []

    # Number the individual ranges to be able to recover the indices later
    combinations = itertools.product(*[enumerate(ranges) for ranges in time_ranges])
    for c in combinations:
        starts = [start for (_, (start, _)) in c]
        ends = [end for (_, (_, end)) in c]

        start = max(starts)
        end = min(ends)
        if start >= end:
            # No overlap
            continue

        duration = end - start + SHP_V1_STEP_WIDTH
        indices = [idx for (idx, _) in c]
        common_ranges.append(
            CommonRange(
                tstart=start, tend=end, duration=duration / 1e9, profile_range_indices=indices
            )
        )

    common_ranges.sort(key=lambda range_: range_.duration, reverse=True)

    return common_ranges


@click.command(short_help="Scan ShpV1 EENV to filter leading de-synched and trailing zero values")
@click.argument(
    "INPUT_FILES",
    type=click.Path(exists=True, resolve_path=True, dir_okay=False, path_type=Path),
    nargs=-1,
    required=True,
)
@click.option(
    "-o",
    "--output-file",
    type=click.Path(resolve_path=True, path_type=Path),
    required=True,
    help="Output file to which the scan report will be written",
)
@click.option(
    "-b",
    "--base-path",
    type=click.Path(exists=True, resolve_path=True, file_okay=False, path_type=Path),
    default="/",
    help="Base path for the energy environment (to write relative paths to the report)",
)
def scan(input_files: list[Path], output_file: Path, base_path: Path) -> None:
    """CLI entrypoint. Scan ShpV1 EENV and generate the report."""
    profiles = []

    # Find individual valid ranges (start and end inclusive)
    # include indices since de-synched parts might cause duplicate timestamps
    for i, file in enumerate(input_files):
        with ShepherdReader(file_path=file) as reader:
            count = reader.samples_n

            continuous_ranges_indices = find_continuous_ranges(ds_time=reader.ds_time, count=count)
            continuous_ranges_times = [
                (int(reader.ds_time[i]), int(reader.ds_time[j]))
                for (i, j) in continuous_ranges_indices
            ]
            o_start = int(reader.ds_time[0])
            o_end = int(reader.ds_time[max([i for (_, i) in continuous_ranges_indices])])
            o_dur = (o_end - o_start + SHP_V1_STEP_WIDTH) / 1e9

            profile = ScanReportProfile(
                original_path=file.relative_to(base_path),
                original_start=o_start,
                original_end=int(o_end),
                original_count=int(count),
                original_duration=o_dur,
                continuous_ranges_indices=continuous_ranges_indices,
                continuous_ranges_times=continuous_ranges_times,
            )
            profiles.append(profile)

    ranges_times = [p.continuous_ranges_times for p in profiles]
    common_ranges = find_common_ranges(ranges_times)

    report = ScanReport(profiles=profiles, common_ranges=common_ranges)

    report.to_file(output_file, minimal=False)


if __name__ == "__main__":
    scan()
