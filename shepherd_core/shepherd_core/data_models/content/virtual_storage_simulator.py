"""Simulator for the virtual storage models / algorithms."""

from collections.abc import Callable

import numpy as np
from matplotlib import pyplot as plt
from pydantic import PositiveFloat
from pydantic import validate_call
from virtual_storage_model import ModelStorage


class StorageSimulator:
    """The simulator benchmarks a set of storage-models.

    - monitors cell-current and voltage, open circuit voltage, state of charge and time
    - takes config with a list of storage-models and timebase
    - runs with a total step-count as config and a current-providing function
        taking time, cell-voltage and SoC as arguments

    The recorded data can be visualized by generating plots.
    """

    def __init__(self, models: list[ModelStorage], dt_s: PositiveFloat) -> None:
        self.models = models
        self.dt_s = dt_s
        for model in self.models:
            if self.dt_s != model.dt_s:
                raise ValueError("timebase on models do not match")
        self.t_s: np.ndarray | None = None

        # models return V_cell, SoC_eff, V_OC
        self.I_input: np.ndarray | None = None
        self.V_OC: np.ndarray | None = None
        self.V_cell: np.ndarray | None = None
        self.SoC: np.ndarray | None = None
        self.SoC_eff: np.ndarray | None = None

    @validate_call
    def run(self, fn: Callable, duration_s: PositiveFloat) -> None:
        self.t_s = np.arange(0, duration_s, self.dt_s)
        self.I_input = np.zeros((len(self.models), self.t_s.shape[0]))
        self.V_OC = np.zeros((len(self.models), self.t_s.shape[0]))
        self.V_cell = np.zeros((len(self.models), self.t_s.shape[0]))
        self.SoC = np.zeros((len(self.models), self.t_s.shape[0]))
        self.SoC_eff = np.zeros((len(self.models), self.t_s.shape[0]))
        for i, model in enumerate(self.models):
            SoC = 1.0
            V_cell = 0.0
            for j, t_s in enumerate(self.t_s):
                I_charge = fn(t_s, SoC, V_cell)
                V_OC, V_cell, SoC, SoC_eff = model.step(I_charge)
                self.I_input[i, j] = I_charge
                self.V_OC[i, j] = V_OC
                self.V_cell[i, j] = V_cell
                self.SoC[i, j] = SoC
                self.SoC_eff[i, j] = SoC_eff

    @validate_call
    def plot(self, title: str, *, plot_delta_v: bool = False) -> None:
        offset = 1 if plot_delta_v else 0
        fig, axs = plt.subplots(4 + offset, 1, sharex="all", figsize=(10, 2 * 6), layout="tight")
        axs[0].set_title(title)
        axs[0].set_ylabel("State of Charge [n]")
        # ⤷ Note: SoC-eff is also available, but unused
        axs[0].grid(visible=True)
        axs[1].set_ylabel("Open-circuit voltage [V]")
        axs[1].grid(visible=True)
        axs[2].set_ylabel("Cell voltage [V]")
        axs[2].grid(visible=True)
        if plot_delta_v:
            axs[3].set_ylabel("Cell voltage delta [V]")
            axs[3].grid(visible=True)
        axs[3 + offset].set_ylabel("Charge current [A]")
        axs[3 + offset].set_xlabel("time [s]")
        axs[3 + offset].grid(visible=True)

        for i, model in enumerate(self.models):
            axs[0].plot(
                self.t_s, self.SoC[i], label=f"{type(model).__name__} {model.cfg.name}", alpha=0.7
            )
            axs[1].plot(self.t_s, self.V_OC[i], label=type(model).__name__, alpha=0.7)
            axs[2].plot(self.t_s, self.V_cell[i], label=type(model).__name__, alpha=0.7)
            if plot_delta_v:  # assumes that timestamps are identical
                axs[3].plot(
                    self.t_s,
                    [v - ref for v, ref in zip(self.V_cell[i], self.V_cell[0], strict=False)],
                    label=type(model).__name__,
                    alpha=0.7,
                )
            axs[3 + offset].plot(self.t_s, self.I_input[i], label=type(model).__name__, alpha=0.7)
        axs[0].legend()
        plt.savefig(title + ".png")
        plt.close(fig)
        plt.clf()
