"""Simulator for the virtual storage models / algorithms."""

from collections.abc import Callable

from matplotlib import pyplot as plt
from virtual_storage import ModelStorage
from virtual_storage import StoragePRUConfig
from virtual_storage import VirtualStorageConfig

# just for validation ATM
lipo = VirtualStorageConfig.lipo(capacity_mAh=600)
lead = VirtualStorageConfig.lead_acid(capacity_mAh=600)
mlcc = VirtualStorageConfig.capacitor(C_uF=600, V_rated=3.6)
cfg_pru_lipo = StoragePRUConfig.from_vstorage(data=lipo)
cfg_pru_lead = StoragePRUConfig.from_vstorage(data=lead)
cfg_pru_mlcc = StoragePRUConfig.from_vstorage(data=mlcc)


class StorageSimulator:
    """The simulator benchmarks a set of storage-models.

    - monitors cell-current and voltage, open circuit voltage, state of charge and time
    - takes config with a list of storage-models and timebase
    - runs with a total step-count as config and a current-providing function
        taking time, cell-voltage and SoC as arguments

    The recorded data can be visualized by generating plots.
    """

    def __init__(self, models: list[ModelStorage], dt_s: float) -> None:
        self.models = models
        self.dt_s = dt_s
        for model in self.models:
            if self.dt_s != model.dt_s:
                raise ValueError("timebase on models do not match")
        self.t_s: list[float] = []

        # models return V_cell, SoC_eff, V_OC
        self.I_input: list[list[float]] = [[] for _ in self.models]
        self.V_cell: list[list[float]] = [[] for _ in self.models]
        self.SoC_eff: list[list[float]] = [[] for _ in self.models]
        self.V_OC: list[list[float]] = [[] for _ in self.models]

    def run(self, fn: Callable, steps: int) -> None:
        self.t_s = [step * self.dt_s for step in range(steps)]
        for i, model in enumerate(self.models):
            SoC_eff = 1.0
            V_cell = 0.0
            for t_s in self.t_s:
                I_cell = fn(t_s, SoC_eff, V_cell)
                V_cell, SoC_eff, V_OC = model.step(I_cell)
                self.I_input[i].append(I_cell)
                self.V_cell[i].append(V_cell)
                self.SoC_eff[i].append(SoC_eff)
                self.V_OC[i].append(V_OC)

    def plot(self, title: str, *, plot_delta_v: bool = False) -> None:
        offset = 1 if plot_delta_v else 0
        fig, axs = plt.subplots(4 + offset, 1, sharex="all", figsize=(10, 2 * 6), layout="tight")
        axs[0].set_title(title)
        axs[0].set_ylabel("State of Charge [n]")
        axs[0].grid(visible=True)
        axs[1].set_ylabel("Open-circuit voltage [V]")
        axs[1].grid(visible=True)
        axs[2].set_ylabel("Cell voltage [V]")
        axs[2].grid(visible=True)
        if plot_delta_v:
            axs[3].set_ylabel("Cell voltage delta [V]")
            axs[3].grid(visible=True)
        axs[3 + offset].set_ylabel("Cell current [A]")
        axs[3 + offset].set_xlabel("time [s]")
        axs[3 + offset].grid(visible=True)

        for i, model in enumerate(self.models):
            axs[0].plot(self.t_s, self.SoC_eff[i], label=type(model).__name__, alpha=0.7)
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
