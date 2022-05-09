"""
Command definitions for CLI
"""
import os
import sys
import logging
from pathlib import Path
from typing import NoReturn

import click
from . import Writer, Reader, __version__

logger = logging.getLogger("SHPData.cli")
verbose_level = 2


def config_logger(verbose: int) -> NoReturn:
    # TODO: put in __init__, provide logger, ditch global var
    if verbose == 0:
        logger.setLevel(logging.ERROR)
    elif verbose == 1:
        logger.setLevel(logging.WARNING)
    elif verbose == 2:
        logger.setLevel(logging.INFO)
    elif verbose > 2:
        logger.setLevel(logging.DEBUG)
    global verbose_level
    verbose_level = verbose
    logging.basicConfig(format="%(message)s")  # reduce internals


def path_to_flist(data_path: Path) -> list[Path]:
    """every path gets transformed to a list of paths
    - if directory: list of files inside
    - if existing file: list with 1 element
    - or else: empty list
    """
    data_path = Path(data_path).absolute()
    h5files = []
    if data_path.is_file() and data_path.suffix == ".h5":
        h5files.append(data_path)
    elif data_path.is_dir():
        flist = os.listdir(data_path)
        for file in flist:
            fpath = data_path / str(file)
            if not fpath.is_file() or ".h5" != fpath.suffix:
                continue
            h5files.append(fpath)
    return h5files


@click.group(context_settings=dict(help_option_names=["-h", "--help"], obj={}))
@click.option(
    "-v",
    "--verbose",
    count=True,
    default=0,
    help="4 Levels [0..3](Error, Warning, Info, Debug)",
)
@click.pass_context
def cli(ctx, verbose: int):
    """Shepherd: Synchronized Energy Harvesting Emulator and Recorder

    Args:
        ctx:
        verbose:
    """
    config_logger(verbose)
    logger.info("Shepherd-Data v%s", __version__)
    logger.debug("Python v%s", sys.version)
    logger.debug("Click v%s", click.__version__)
    if not ctx.invoked_subcommand:
        click.echo("Please specify a command")


@cli.command(short_help="Validates a file or directory containing shepherd-recordings")
@click.argument("in_data", type=click.Path(exists=True, resolve_path=True))
def validate(in_data):
    """Validates a file or directory containing shepherd-recordings
    """
    files = path_to_flist(in_data)
    valid_dir = True
    for file in files:
        logger.info("Validating '%s' ...", file.name)
        valid_file = True
        with Reader(file, verbose=verbose_level >= 2) as shpr:
            valid_file &= shpr.is_valid()
            valid_file &= shpr.check_timediffs()
            valid_dir &= valid_file
            if not valid_file:
                logger.error(" -> File '%s' was NOT valid", file.name)
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
def extract(in_data, ds_factor, separator):
    """Extracts recorded IVSamples and stores it to csv
    """
    files = path_to_flist(in_data)
    if not isinstance(ds_factor, (float, int)) or ds_factor < 1:
        ds_factor = 1000
        logger.info("DS-Factor was invalid was reset to 1'000")
    for file in files:
        logger.info("Extracting IV-Samples from '%s' ...", file.name)
        with Reader(file, verbose=verbose_level >= 2) as shpr:
            # will create a downsampled h5-file (if not existing) and then saving to csv
            ds_file = file.with_suffix(f".downsampled_x{round(ds_factor)}.h5")
            if not ds_file.exists():
                logger.info("Downsampling '%s' by factor x%s ...", file.name, ds_factor)
                with Writer(
                    ds_file,
                    mode=shpr.get_mode(),
                    datatype=shpr.get_datatype(),
                    window_samples=shpr.get_window_samples(),
                    cal_data=shpr.get_calibration_data(),
                    verbose=verbose_level >= 2,
                ) as shpw:
                    shpw["ds_factor"] = ds_factor
                    shpw.set_hostname(shpr.get_hostname())
                    shpw.set_config(shpr.get_config())
                    shpr.downsample(
                        shpr.ds_time, shpw.ds_time, ds_factor=ds_factor, is_time=True
                    )
                    shpr.downsample(
                        shpr.ds_voltage, shpw.ds_voltage, ds_factor=ds_factor
                    )
                    shpr.downsample(
                        shpr.ds_current, shpw.ds_current, ds_factor=ds_factor
                    )

            with Reader(ds_file, verbose=verbose_level >= 2) as shpd:
                shpd.save_csv(shpd["data"], separator)


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
def extract_meta(in_data, separator):
    """Extracts metadata and logs from file or directory containing shepherd-recordings
    """
    files = path_to_flist(in_data)
    for file in files:
        logger.info("Extracting metadata & logs from '%s' ...", file.name)
        with Reader(file, verbose=verbose_level >= 2) as shpr:
            elements = shpr.save_metadata()

            if "sysutil" in elements:
                shpr.save_csv(shpr["sysutil"], separator)
            if "timesync" in elements:
                shpr.save_csv(shpr["timesync"], separator)

            if "dmesg" in elements:
                shpr.save_log(shpr["dmesg"])
            if "exceptions" in elements:
                shpr.save_log(shpr["exceptions"])
            if "uart" in elements:
                shpr.save_log(shpr["uart"])


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
    type=int,
    help="Alternative Input to determine a downsample-factor (Choose One)",
)
def downsample(in_data, ds_factor, sample_rate):
    """Creates an array of downsampling-files from file or directory containing shepherd-recordings
    """
    if ds_factor is None and sample_rate is not None and sample_rate >= 1:
        ds_factor = int(Reader.samplerate_sps / sample_rate)
    if isinstance(ds_factor, (float, int)) and ds_factor >= 1:
        ds_list = [ds_factor]
    else:
        ds_list = [5, 25, 100, 500, 2_500, 10_000, 50_000, 250_000, 1_000_000]

    files = path_to_flist(in_data)
    for file in files:
        with Reader(file, verbose=verbose_level >= 2) as shpr:
            for _factor in ds_list:
                if shpr.ds_time.shape[0] / _factor < 1000:
                    logger.warning("will skip downsampling for %s because resulting sample-size is too small")
                    break
                ds_file = file.with_suffix(f".downsampled_x{round(_factor)}.h5")
                if ds_file.exists():
                    continue
                logger.info("Downsampling '%s' by factor x%s ...", file.name, _factor)
                with Writer(
                    ds_file,
                    mode=shpr.get_mode(),
                    datatype=shpr.get_datatype(),
                    window_samples=shpr.get_window_samples(),
                    cal_data=shpr.get_calibration_data(),
                    verbose=verbose_level >= 2,
                ) as shpw:
                    shpw["ds_factor"] = _factor
                    shpw.set_hostname(shpr.get_hostname())
                    shpw.set_config(shpr.get_config())
                    shpr.downsample(
                        shpr.ds_time, shpw.ds_time, ds_factor=_factor, is_time=True
                    )
                    shpr.downsample(
                        shpr.ds_voltage, shpw.ds_voltage, ds_factor=_factor
                    )
                    shpr.downsample(
                        shpr.ds_current, shpw.ds_current, ds_factor=_factor
                    )


@cli.command(
    short_help="Plots IV-trace from file or directory containing shepherd-recordings"
)
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
def plot(in_data, start: float, end: float, width: int, height: int, multiplot: bool):
    """ Plots IV-trace from file or directory containing shepherd-recordings
    """
    files = path_to_flist(in_data)
    multiplot = multiplot and len(files) > 1
    data = []
    for file in files:
        logger.info("Generating plot for '%s' ...", file.name)
        with Reader(file, verbose=verbose_level >= 2) as shpr:
            if multiplot:
                data.append(shpr.generate_plot_data(start, end, relative_ts=True))
            else:
                shpr.plot_to_file(start, end, width, height)
    if multiplot:
        logger.info(f"Got {len(data)} datasets to plot")
        mpl_path = Reader.multiplot_to_file(data, in_data, width, height)
        logger.info("Plot generated and saved to '%s'", mpl_path.name)


if __name__ == "__main__":
    print("This File should not be executed like this ...")
    cli()
