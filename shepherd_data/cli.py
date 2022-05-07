import os
import click
import logging
from pathlib import Path

from shepherd_data import Writer, Reader


logger = logging.getLogger("SHPData.cli")
# consoleHandler = logging.StreamHandler()
# logger.addHandler(consoleHandler)
verbose_level = 2


def config_logger(verbose: int):
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


def path_to_flist(data_path: Path) -> list[Path]:
    data_path = Path(data_path)
    h5files = []
    if data_path.is_file() and data_path.suffix == ".h5":
        h5files.append(data_path)
    elif data_path.is_dir:
        flist = os.listdir(data_path)
        for file in flist:
            fpath = Path(file)
            if not fpath.is_file() or ".h5" != fpath.suffix:
                continue
            h5files.append(fpath)
    return h5files


@click.group(context_settings=dict(help_option_names=["-h", "--help"], obj={}))
@click.option(
    "-v",
    "--verbose",
    count=True,
    default=2,
    help="4 Levels (Error, Warning, Info, Debug)",
)
@click.pass_context
def cli(ctx, verbose: int):
    """Shepherd: Synchronized Energy Harvesting Emulator and Recorder

    Args:
        ctx:
        verbose:
    Returns:
    """
    config_logger(verbose)


@cli.command(short_help="Validates a file or directory containing shepherd-recordings")
@click.argument("in_data", type=click.Path(exists=True, resolve_path=True))
def validate(in_data):
    files = path_to_flist(in_data)
    valid_dir = True
    for file in files:
        logger.info(f"Validating '{file.name}' ...")
        valid_file = True
        with Reader(file, verbose=verbose_level > 2) as shpr:
            valid_file &= shpr.is_valid()
            valid_file &= shpr.check_timediffs()
            valid_dir &= valid_file
            if not valid_file:
                logger.error(f" -> File '{file.name}' was NOT valid")
    return not valid_dir


@cli.command(short_help="Extracts recorded IVSamples and stores it to csv")
@click.argument("in_data", type=click.Path(exists=True, resolve_path=True))
@click.option(
    "--ds_factor",
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
    files = path_to_flist(in_data)
    if not isinstance(ds_factor, (float, int)) or ds_factor < 1:
        ds_factor = 1000
        logger.info(f"DS-Factor was invalid was reset to 1'000")
    for file in files:
        logger.info(f"Extracting IV-Samples from '{file.name}' ...")
        with Reader(file, verbose=verbose_level > 2) as shpr:
            # will create a downsampled h5-file (if not existing) and then saving to csv
            ds_file = file.with_suffix(f".downsampled_x{round(ds_factor)}.h5")
            if not ds_file.exists():
                logger.info(f"Downsampling '{file.name}' by factor x{ds_factor} ...")
                with Writer(
                    ds_file,
                    mode=shpr.get_mode(),
                    calibration_data=shpr.get_calibration_data(),
                    verbose=verbose_level > 2,
                ) as shpw:
                    shpw["ds_factor"] = ds_factor
                    shpr.downsample(
                        shpr.ds_time, shpw.ds_time, ds_factor=ds_factor, is_time=True
                    )
                    shpr.downsample(
                        shpr.ds_voltage, shpw.ds_voltage, ds_factor=ds_factor
                    )
                    shpr.downsample(
                        shpr.ds_current, shpw.ds_current, ds_factor=ds_factor
                    )

            with Reader(ds_file, verbose=verbose_level > 2) as shpd:
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
    files = path_to_flist(in_data)
    for file in files:
        logger.info(f"Extracting metadata & logs from '{file.name}' ...")
        with Reader(file, verbose=verbose_level > 2) as shpr:
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
    short_help="Creates an array of downsampling-files from file or directory containing shepherd-recordings"
)
@click.argument("in_data", type=click.Path(exists=True, resolve_path=True))
# @click.option("--out_data", "-o", type=click.Path(resolve_path=True))
@click.option(
    "--ds_factor",
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
    if ds_factor is None and sample_rate is not None and sample_rate >= 1:
        ds_factor = int(Reader.samplerate_sps / sample_rate)
    if isinstance(ds_factor, (float, int)) and ds_factor >= 1:
        ds_list = [ds_factor]
    else:
        ds_list = [5, 25, 100, 500, 2_500, 10_000, 50_000, 250_000, 1_000_000]

    files = path_to_flist(in_data)
    for file in files:
        with Reader(file, verbose=verbose_level > 2) as shpr:
            for ds_factor in ds_list:
                if shpr.ds_time.shape[0] / ds_factor < Reader.samplerate_sps:
                    break
                ds_file = file.with_suffix(f".downsampled_x{ds_factor}.h5")
                if ds_file.exists():
                    continue
                logger.info(f"Downsampling '{file.name}' by factor x{ds_factor} ...")
                with Writer(
                    ds_file,
                    mode=shpr.get_mode(),
                    datatype=shpr.get_datatype(),
                    calibration_data=shpr.get_calibration_data(),
                    verbose=verbose_level > 2,
                ) as shpw:
                    shpw["ds_factor"] = ds_factor
                    shpr.downsample(
                        shpr.ds_time, shpw.ds_time, ds_factor=ds_factor, is_time=True
                    )
                    shpr.downsample(
                        shpr.ds_voltage, shpw.ds_voltage, ds_factor=ds_factor
                    )
                    shpr.downsample(
                        shpr.ds_current, shpw.ds_current, ds_factor=ds_factor
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
    logger.info(
        f"CLI-options are start = {start} s, end= {end} s, width = {width}, height = {height}"
    )
    files = path_to_flist(in_data)
    multiplot = multiplot and len(files) > 1
    data = []
    for file in files:
        logger.info(f"Generating plot for '{file.name}' ...")
        with Reader(file, verbose=verbose_level > 2) as shpr:
            if multiplot:
                data.append(shpr.generate_plot_data(start, end, relative_ts=True))
            else:
                shpr.plot_to_file(start, end, width, height)
    if multiplot:
        Reader.multiplot_to_file(data, in_data, width, height)


if __name__ == "__main__":
    cli()
