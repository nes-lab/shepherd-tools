import os
import click
import time
import logging
from pathlib import Path

from shepherd_data import Writer, Reader

consoleHandler = logging.StreamHandler()
logger = logging.getLogger("shepherd_cli")
logger.addHandler(consoleHandler)
verbose_level = 0

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
@click.option("-v", "--verbose", count=True, default=2, help="4 Levels (Error, Warning, Info, Debug)")
@click.pass_context
def cli(ctx, verbose: int):
    """ Shepherd: Synchronized Energy Harvesting Emulator and Recorder

    Args:
        ctx:
        verbose:
    Returns:
    """
    config_logger(verbose)


@cli.command(short_help="Validates a file or directory containing shepherd-recordings")
@click.argument("database", type=click.Path(exists=True, ))
def validate(database):
    files = path_to_flist(database)
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


@cli.command(short_help="Extracts metadata and logs from file or directory containing shepherd-recordings")
@click.argument("database", type=click.Path(exists=True, ))
def extract(database):
    files = path_to_flist(database)
    for file in files:
        logger.info(f"Extracting data from '{file.name}' ...")
        with Reader(file, verbose=verbose_level > 2) as shpr:
            elements = shpr.save_metadata()

            if "sysutil" in elements:
                shpr.save_csv(shpr["sysutil"])
            if "timesync" in elements:
                shpr.save_csv(shpr["timesync"])

            if "dmesg" in elements:
                shpr.save_log(shpr["dmesg"])
            if "exceptions" in elements:
                shpr.save_log(shpr["exceptions"])
            if "uart" in elements:
                shpr.save_log(shpr["uart"])


@cli.command(short_help="Plots IV-trace from file or directory containing shepherd-recordings")
@click.argument("database", type=click.Path(exists=True, ))
@click.option("--start", "-s", default=None, type=click.FLOAT, help="Start of plot in seconds, will be 0 if omitted")
@click.option("--end", "-e", default=None, type=click.FLOAT, help="End of plot in seconds, will be max if omitted")
@click.option("--width", "-w", default=20, type=click.INT, help="Width-Dimension of resulting plot")
@click.option("--height", "-h", default=10, type=click.INT, help="Height-Dimension of resulting plot")
def plot(database, start: float, end: float, width: int, height: int, ):
    logger.info(f"CLI-options are start = {start} s, end= {end} s, width = {width}, height = {height}")
    files = path_to_flist(database)
    for file in files:
        logger.info(f"Generating plot for '{file.name}' ...")
        with Reader(file, verbose=verbose_level > 2) as shpr:
            shpr.plot_to_file(start, end, width, height)
            # todo: group-plot


@cli.command(short_help="Creates an array of downsampling-files from file or directory containing shepherd-recordings")
@click.argument("database", type=click.Path(exists=True, ))
def downsample(database):
    ds_list = [5, 25, 100, 500, 2_500, 10_000, 50_000, 250_000, 1_000_000]
    files = path_to_flist(database)
    for file in files:
        with Reader(file, verbose=verbose_level > 2) as shpr:
            for ds_factor in ds_list:
                if shpr.ds_time.shape[0] / ds_factor < Reader.samplerate_sps:
                    break
                ds_file = file.with_suffix(f".downsampled_x{ds_factor}.h5")
                if ds_file.exists():
                    continue
                logger.info(f"Downsampling '{file.name}' by factor x{ds_factor} ...")
                with Writer(ds_file, mode=shpr.get_mode(), calibration_data=shpr.get_calibration_data(), verbose=verbose_level > 2) as shpw:
                    shpw["ds_factor"] = ds_factor
                    shpr.downsample(shpr.ds_time, shpw.ds_time, ds_factor=ds_factor, is_time=True)
                    shpr.downsample(shpr.ds_voltage, shpw.ds_voltage, ds_factor=ds_factor)
                    shpr.downsample(shpr.ds_current, shpw.ds_current, ds_factor=ds_factor)


if __name__ == "__main__":
    cli()
