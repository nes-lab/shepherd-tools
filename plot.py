import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import click
import h5py

from mppt import find_oc


@click.command()
@click.argument("database", type=click.Path(exists=True, dir_okay=False))
def cli(database):
    with h5py.File(database, "r") as db:
        tt = db["data"]["time"][:].astype(float) / 1e9
        if db.attrs["type"] == "SHEPHERD_REGVOLTAGE":
            vv = db["data"]["voltage"][:].astype(float) / 1e6
            plt.plot(tt, vv)
            plt.xlabel("Time [s]")
            plt.ylabel("Voltage [V]")
            plt.ylim((0, plt.ylim()[1]))

        elif db.attrs["type"] == "SHEPHERD_IVTRACE":
            _, axes = plt.subplots(2, 1, sharex=True)
            vv = db["data"]["voltage"][:].astype(float) / 1e6
            ii = db["data"]["current"][:].astype(float) / 1e6

            axes[0].plot(tt, vv)
            axes[0].set_ylabel("Voltage [V]")
            axes[1].plot(tt, ii)
            axes[1].set_ylabel("Current [mA]")
            axes[1].set_xlabel("Time [s]")

        elif db.attrs["type"] == "SHEPHERD_IVCURVE":
            voc_proto = find_oc(
                db["proto_curve"]["voltage"][:], db["proto_curve"]["current"][:]
            )
            isc_proto = db["proto_curve"]["current"][0]

            trans_coeffs = db["data"]["trans_coeffs"][:].astype(float) / (2 ** 24) + 1.0

            _, axes = plt.subplots(2, 1, sharex=True)
            voc = float(voc_proto) * trans_coeffs[:, 0] / 1e6
            isc = float(isc_proto) * trans_coeffs[:, 1] / 1e6
            axes[0].plot(tt, voc)
            axes[0].set_ylabel("Voltage [V]")
            axes[1].plot(tt, isc)
            axes[1].set_ylabel("Current [mA]")
            axes[1].set_xlabel("Time [s]")
        else:
            raise Exception(f"Database type {db.attrs['type']} not supported")
        plt.show()


if __name__ == "__main__":
    cli()