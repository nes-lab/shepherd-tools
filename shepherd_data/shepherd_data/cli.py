"""Command definitions for CLI
"""
import logging
import os
import sys
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import List
from typing import Optional

import click

from shepherd_core import get_verbose_level
from shepherd_core import increase_verbose_level
from shepherd_core import local_tz
from shepherd_core.commons import samplerate_sps_default

from . import Reader
from . import Writer
from . import __version__

logger = logging.getLogger("SHPData.cli")


def path_to_flist(data_path: Path) -> List[Path]:
    """Every path gets transformed to a list of paths
    - if directory: list of files inside
    - if existing file: list with 1 element
    - or else: empty list
    """
    data_path = Path(data_path).resolve()
    h5files = []
    if data_path.is_file() and data_path.suffix.lower() == ".h5":
        h5files.append(data_path)
    elif data_path.is_dir():
        flist = os.listdir(data_path)
        for file in flist:
            fpath = data_path / str(file)
            if not fpath.is_file() or fpath.suffix.lower() != ".h5":
                continue
            h5files.append(fpath)
    return h5files


@click.group(context_settings={"help_option_names": ["-h", "--help"], "obj": {}})
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="4 Levels [0..3](Error, Warning, Info, Debug)",
)
@click.option(
    "--version",
    is_flag=True,
    help="Prints version-info at start (combinable with -v)",
)
@click.pass_context  # TODO: is the ctx-type correct?
def cli(ctx: click.Context, verbose: bool, version: bool) -> None:  # noqa: FBT001
    """Shepherd: Synchronized Energy Harvesting Emulator and Recorder"""
    if verbose:
        increase_verbose_level(3)
    if version:
        logger.info("Shepherd-Data v%s", __version__)
        logger.debug("Python v%s", sys.version)
        logger.debug("Click v%s", click.__version__)
    if not ctx.invoked_subcommand:
        click.echo("Please specify a valid command")


@cli.command(short_help="Validates a file or directory containing shepherd-recordings")
@click.argument("in_data", type=click.Path(exists=True, resolve_path=True))
def validate(in_data: Path) -> None:
    """Validates a file or directory containing shepherd-recordings"""
    files = path_to_flist(in_data)
    verbose_level = get_verbose_level()  # TODO: should be stored and passed in ctx
    valid_dir = True
    for file in files:
        logger.info("Validating '%s' ...", file.name)
        valid_file = True
        try:
            with Reader(file, verbose=verbose_level > 2) as shpr:
                valid_file &= shpr.is_valid()
                valid_file &= shpr.check_timediffs()
                valid_dir &= valid_file
                if not valid_file:
                    logger.error(" -> File '%s' was NOT valid", file.name)
        except TypeError as _xpc:
            logger.error("ERROR: will skip file, caught exception: %s", _xpc)
    sys.exit(int(not valid_dir))


@cli.command(short_help="Extracts recorded IVSamples and stores it to csv")
@click.argument("in_data", type=click.Path(exists=True, resolve_path=True))
@click.option(
    "--ds-factor",
    "-f",
    default=1000,
    type=click.FLOAT,
    help="Downsample-Factor, if one specific value is wanted",
)
@click.option(
    "--separator",
    "-s",
    default=";",
    type=click.STRING,
    help="Set an individual csv-separator",
)
def extract(in_data: Path, ds_factor: float, separator: str) -> None:
    """Extracts recorded IVSamples and stores it to csv"""
    files = path_to_flist(in_data)
    verbose_level = get_verbose_level()
    if not isinstance(ds_factor, (float, int)) or ds_factor < 1:
        ds_factor = 1000
        logger.info("DS-Factor was invalid was reset to 1'000")
    for file in files:
        logger.info("Extracting IV-Samples from '%s' ...", file.name)
        try:
            with Reader(file, verbose=verbose_level > 2) as shpr:
                # will create a downsampled h5-file (if not existing) and then saving to csv
                ds_file = file.with_suffix(f".downsampled_x{round(ds_factor)}.h5")
                if not ds_file.exists():
                    logger.info("Downsampling '%s' by factor x%f ...", file.name, ds_factor)
                    with Writer(
                        ds_file,
                        mode=shpr.get_mode(),
                        datatype=shpr.get_datatype(),
                        window_samples=shpr.get_window_samples(),
                        cal_data=shpr.get_calibration_data(),
                        verbose=verbose_level > 2,
                    ) as shpw:
                        shpw["ds_factor"] = ds_factor
                        shpw.store_hostname(shpr.get_hostname())
                        shpw.store_config(shpr.get_config())
                        shpr.downsample(
                            shpr.ds_time,
                            shpw.ds_time,
                            ds_factor=ds_factor,
                            is_time=True,
                        )
                        shpr.downsample(shpr.ds_voltage, shpw.ds_voltage, ds_factor=ds_factor)
                        shpr.downsample(shpr.ds_current, shpw.ds_current, ds_factor=ds_factor)

                with Reader(ds_file, verbose=verbose_level > 2) as shpd:
                    shpd.save_csv(shpd["data"], separator)
        except TypeError as _xpc:
            logger.error("ERROR: will skip file, caught exception: %s", _xpc)


@cli.command(
    short_help="Extracts metadata and logs from file or directory containing shepherd-recordings"
)
@click.argument("in_data", type=click.Path(exists=True, resolve_path=True))
@click.option(
    "--separator",
    "-s",
    default=";",
    type=click.STRING,
    help="Set an individual csv-separator",
)
def extract_meta(in_data: Path, separator: str) -> None:
    """Extracts metadata and logs from file or directory containing shepherd-recordings"""
    files = path_to_flist(in_data)
    verbose_level = get_verbose_level()
    for file in files:
        logger.info("Extracting metadata & logs from '%s' ...", file.name)
        # TODO: add default exports (user-centric) and allow specifying --all or specific ones
        # TODO: could also be combined with other extractors (just have one)
        # TODO remove deprecated: timesync; "shepherd-log", "dmesg", "exceptions"
        try:
            with Reader(file, verbose=verbose_level > 2) as shpr:
                shpr.save_metadata()
                for element in ["ptp", "sysutil", "timesync"]:
                    if element in shpr.h5file:
                        shpr.save_csv(shpr[element], separator)
                logs_depr = ["shepherd-log", "dmesg", "exceptions"]
                logs = ["sheep", "kernel", "phc2sys", "uart"]
                for element in logs + logs_depr:
                    if element in shpr.h5file:
                        shpr.save_log(shpr[element])
                        # TODO: allow omitting timestamp,
                        #       also test if segmented uart is correctly written
                        shpr.warn_logs(element, show=True)
        except TypeError as _xpc:
            logger.error("ERROR: will skip file, caught exception: %s", _xpc)


@cli.command(
    short_help="Extracts uart from gpio-trace in file or directory containing shepherd-recordings"
)
@click.argument("in_data", type=click.Path(exists=True, resolve_path=True))
def extract_uart(in_data: Path) -> None:
    """Extracts uart from gpio-trace in file or directory containing shepherd-recordings"""
    files = path_to_flist(in_data)
    verbose_level = get_verbose_level()
    for file in files:
        logger.info("Extracting uart from gpio-trace from from '%s' ...", file.name)
        try:
            with Reader(file, verbose=verbose_level > 2) as shpr:
                # TODO: move into separate fn OR add to h5-file and use .save_log(), ALSO TEST
                lines = shpr.gpio_to_uart()
                # TODO: could also add parameter to get symbols instead of lines
                log_path = Path(file).with_suffix(".uart_from_wf.log")
                if log_path.exists():
                    logger.info("File already exists, will skip '%s'", log_path.name)
                    continue

                with log_path.open("w") as log_file:
                    for line in lines:
                        with suppress(TypeError):
                            timestamp = datetime.fromtimestamp(float(line[0]), tz=local_tz())
                            log_file.write(timestamp.strftime("%Y-%m-%d %H:%M:%S.%f") + ":")
                            # TODO: allow to skip Timestamp and export raw text
                            log_file.write(f"\t{str.encode(line[1])}")
                            log_file.write("\n")
        except TypeError as _xpc:
            logger.error("ERROR: will skip file, caught exception: %s", _xpc)


@cli.command(short_help="Extracts gpio-trace from file or directory containing shepherd-recordings")
@click.argument("in_data", type=click.Path(exists=True, resolve_path=True))
@click.option(
    "--separator",
    "-s",
    default=";",
    type=click.STRING,
    help="Set an individual csv-separator",
)
def extract_gpio(in_data: Path, separator: str) -> None:
    """Extracts uart from gpio-trace in file or directory containing shepherd-recordings"""
    files = path_to_flist(in_data)
    verbose_level = get_verbose_level()
    for file in files:
        logger.info("Extracting gpio-trace from from '%s' ...", file.name)
        try:
            with Reader(file, verbose=verbose_level > 2) as shpr:
                wfs = shpr.gpio_to_waveforms()
                for name, wf in wfs.items():
                    shpr.waveform_to_csv(name, wf, separator)
        except TypeError as _xpc:
            logger.error("ERROR: will skip file, caught exception: %s", _xpc)


@cli.command(
    short_help="Creates an array of downsampling-files from "
    "file or directory containing shepherd-recordings"
)
@click.argument("in_data", type=click.Path(exists=True, resolve_path=True))
# @click.option("--out_data", "-o", type=click.Path(resolve_path=True))
@click.option(
    "--ds-factor",
    "-f",
    default=None,
    type=click.FLOAT,
    help="Downsample-Factor, if one specific value is wanted",
)
@click.option(
    "--sample-rate",
    "-r",
    type=click.INT,
    help="Alternative Input to determine a downsample-factor (Choose One)",
)
def downsample(in_data: Path, ds_factor: Optional[float], sample_rate: Optional[int]) -> None:
    """Creates an array of downsampling-files from file
    or directory containing shepherd-recordings
    """
    if ds_factor is None and sample_rate is not None and sample_rate >= 1:
        ds_factor = int(samplerate_sps_default / sample_rate)
        # TODO: shouldn't current sps be based on file rather than default?
    if isinstance(ds_factor, (float, int)) and ds_factor >= 1:
        ds_list = [ds_factor]
    else:
        ds_list = [5, 25, 100, 500, 2_500, 10_000, 50_000, 250_000, 1_000_000]

    files = path_to_flist(in_data)
    verbose_level = get_verbose_level()
    for file in files:
        try:
            with Reader(file, verbose=verbose_level > 2) as shpr:
                for _factor in ds_list:
                    if shpr.ds_voltage.shape[0] / _factor < 1000:
                        logger.warning(
                            "will skip downsampling for %s because "
                            "resulting sample-size is too small",
                            file.name,
                        )
                        break
                    ds_file = file.with_suffix(f".downsampled_x{round(_factor)}.h5")
                    if ds_file.exists():
                        continue
                    logger.info("Downsampling '%s' by factor x%f ...", file.name, _factor)
                    with Writer(
                        ds_file,
                        mode=shpr.get_mode(),
                        datatype=shpr.get_datatype(),
                        window_samples=shpr.get_window_samples(),
                        cal_data=shpr.get_calibration_data(),
                        verbose=verbose_level > 2,
                    ) as shpw:
                        shpw["ds_factor"] = _factor
                        shpw.store_hostname(shpr.get_hostname())
                        shpw.store_config(shpr.get_config())
                        shpr.downsample(shpr.ds_time, shpw.ds_time, ds_factor=_factor, is_time=True)
                        shpr.downsample(shpr.ds_voltage, shpw.ds_voltage, ds_factor=_factor)
                        shpr.downsample(shpr.ds_current, shpw.ds_current, ds_factor=_factor)
        except TypeError as _xpc:
            logger.error("ERROR: will skip file, caught exception: %s", _xpc)


@cli.command(short_help="Plots IV-trace from file or directory containing shepherd-recordings")
@click.argument("in_data", type=click.Path(exists=True, resolve_path=True))
@click.option(
    "--start",
    "-s",
    default=None,
    type=click.FLOAT,
    help="Start of plot in seconds, will be 0 if omitted",
)
@click.option(
    "--end",
    "-e",
    default=None,
    type=click.FLOAT,
    help="End of plot in seconds, will be max if omitted",
)
@click.option(
    "--width",
    "-w",
    default=20,
    type=click.INT,
    help="Width-Dimension of resulting plot",
)
@click.option(
    "--height",
    "-h",
    default=10,
    type=click.INT,
    help="Height-Dimension of resulting plot",
)
@click.option(
    "--multiplot",
    "-m",
    is_flag=True,
    help="Plot all files (in directory) into one Multiplot",
)
def plot(
    in_data: Path,
    start: Optional[float],
    end: Optional[float],
    width: int,
    height: int,
    multiplot: bool,  # noqa: FBT001
) -> None:
    """Plots IV-trace from file or directory containing shepherd-recordings"""
    files = path_to_flist(in_data)
    verbose_level = get_verbose_level()
    multiplot = multiplot and len(files) > 1
    data = []
    for file in files:
        logger.info("Generating plot for '%s' ...", file.name)
        try:
            with Reader(file, verbose=verbose_level > 2) as shpr:
                if multiplot:
                    data.append(shpr.generate_plot_data(start, end, relative_timestamp=True))
                else:
                    shpr.plot_to_file(start, end, width, height)
        except TypeError as _xpc:
            logger.error("ERROR: will skip file, caught exception: %s", _xpc)
    if multiplot:
        logger.info("Got %d datasets to plot", len(data))
        mpl_path = Reader.multiplot_to_file(data, in_data, width, height)
        if mpl_path:
            logger.info("Plot generated and saved to '%s'", mpl_path.name)
        else:
            logger.info("Plot not generated, path was already in use.")


if __name__ == "__main__":
    logger.info("This File should not be executed like this ...")
    cli()
