"""I-V Surface generation script for a multivariate random walk of sample PV panels."""

import math
from collections.abc import Callable
from multiprocessing import Pool
from multiprocessing import cpu_count
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from commons import EEnvGenerator
from commons import common_seed
from commons import process_sp
from commons import root_storage_default
from pydantic import BaseModel
from scipy import constants as const
from scipy.optimize import newton
from scipy.special import lambertw
from shepherd_core.data_models import EnergyDType
from shepherd_core.data_models import EnergyEnvironment
from shepherd_core.data_models import EnergyProfile
from shepherd_core.data_models import Wrapper
from shepherd_core.logger import log
from typing_extensions import Self


class Params(BaseModel):
    """Config model with default parameters."""

    root_path: Path = root_storage_default
    dir_name: str = "synthetic_multivariate_random_walk"
    duration: int = 1 * 60 * 60
    chunk_size: int = 2_000_000
    # custom config below
    node_count: int = 20
    # 1 combinations, 20 nodes, 1h
    description: str = (
        "I-V Surface of an emulated PV cell setup. "
        "Uses a multivariate random walk to determine open-circuit voltages for the cells. "
        "Uses the given PV panel model to calculate terminal current at given terminal voltage. "
        "Applies a voltage ramp to generate I-V surfaces."
    )
    metadata: dict[str, Any] = {
        "seed": common_seed,
        "energy type": "light",
        "energy source": "multivariate random walk that mimics natural sun light and clouds",
        "transducer": "ANYSOLAR KXOB201K04F (PV)",
        "temperature": "25 degC",
    }


params_default = Params()
path_file: Path = Path(__file__)


class SDMNoRP:
    """
    Single diode model using datasheet parameters.

    See: https://doi.org/10.1109/ICIINFS.2011.6038128
    """

    k: float = const.Boltzmann
    q: float = const.elementary_charge
    T_stc: float = 25 + const.zero_Celsius  # 25 C in Kelvin
    g_stc: float = 1000  # W/m2

    def __init__(
        self,
        name: str,
        I_SC_stc: float,
        V_OC_stc: float,
        V_MP_stc: float,
        I_MP_stc: float,
        n_s: int,
        dI_SCdt: float,
        dV_OCdt: float,
        t: float,
    ) -> None:
        self.name = name
        self.I_SC_stc = I_SC_stc
        self.V_OC_stc = V_OC_stc
        self.V_MP_stc = V_MP_stc
        self.I_MP_stc = I_MP_stc
        self.n_s = n_s
        self.dI_SCdt = dI_SCdt
        self.dV_OCdt = dV_OCdt

        # --- Precompute n (diode ideality factor) ---
        m_stc = self.q / (n_s * self.k * self.T_stc)

        def f(n: float) -> float:
            # Equation 6
            I_0_stc = I_SC_stc / (math.exp(m_stc * V_OC_stc / n) - 1)
            # Equation 18
            return n * I_MP_stc + (I_SC_stc - I_MP_stc + I_0_stc) * (
                n * math.log((I_SC_stc - I_MP_stc + I_0_stc) / I_0_stc) - 2 * m_stc * V_MP_stc
            )

        def df(n: float) -> float:
            # Equation 6
            I_0_stc = I_SC_stc / (math.exp(m_stc * V_OC_stc / n) - 1)
            # Equation 20
            dI_0dn = (
                m_stc
                * V_OC_stc
                * I_SC_stc
                * math.exp(m_stc * V_OC_stc / n)
                / (n**2 * (math.exp(m_stc * V_OC_stc / n) - 1) ** 2)
            )
            # Equation 19
            return (
                I_MP_stc
                + dI_0dn
                * (n * math.log((I_SC_stc - I_MP_stc + I_0_stc) / I_0_stc) - 2 * m_stc * V_MP_stc)
                + (
                    I_SC_stc
                    - I_MP_stc
                    + I_0_stc
                    * (
                        math.log((I_SC_stc - I_MP_stc + I_0_stc) / I_0_stc)
                        - n
                        * (I_SC_stc - I_MP_stc)
                        / ((I_SC_stc - I_MP_stc + I_0_stc) * I_0_stc)
                        * dI_0dn
                    )
                )
            )

        # Equation 22
        self.n = newton(func=f, fprime=df, x0=1, tol=1e-3, maxiter=10000)
        # ---

        # --- Precompute r_s ---
        # Equation 6
        I_0_stc = self.I_SC_stc / (math.exp(m_stc / self.n * self.V_OC_stc) - 1)

        # Equation 8
        self.r_s = (
            self.n
            / (m_stc * self.I_MP_stc)
            * math.log((self.I_SC_stc - self.I_MP_stc + I_0_stc) / I_0_stc)
            - self.V_MP_stc / self.I_MP_stc
        )
        # ---

        # --- Precompute various subexpressions ---
        # v_oc at g=g_stc
        self.V_OC_stcg = self.V_OC_stc + self.dV_OCdt * (t - self.T_stc)
        # m (from Equation 2) over n
        self.mn = self.q / (t * self.n * self.n_s * self.k)
        # delta i_sc over delta (g/g_stc)
        self.dI_SCdgg_stc = self.I_SC_stc * (1 + self.dI_SCdt * (t - self.T_stc))
        # ---

    def get_i(self, V: float, V_OC: float) -> float:
        # Get required g/g_stc to reach the specified v_oc
        # Derived from Equation 5
        gg_stc = math.exp((V_OC - self.V_OC_stcg) * self.mn)

        # Get model parameters
        # Equation 4
        I_SC = gg_stc * self.dI_SCdgg_stc
        # Equation 5
        V_OC = self.V_OC_stcg + math.log(gg_stc) / self.mn
        # Equation 3
        I_ph = I_SC
        # Equation 6
        I_0 = I_SC / (math.exp(self.mn * V_OC) - 1)

        # Calculate current using lambert-w function
        #
        # Original SDM Equation: i = i_pv - i_0 * (exp(mn * (v + i * r_s)) - 1)
        # where mn = q / (n_s * k * t * n)
        #
        # Conditions:
        #     i_0 != 0; otherwise the diodes in the SDM becomes meaningless
        #     mn != 0; true since q != 0
        #     r_s != 0; otherwise we have SDM without series resistance
        tmp1 = I_0 * self.mn * self.r_s * math.exp(self.mn * (I_ph * self.r_s + I_0 * self.r_s + V))
        tmp2 = lambertw(tmp1)
        if tmp2.imag != 0:
            msg = f"Lambert-W result is not a real number: W({tmp1}) = {tmp2}"
            raise RuntimeError(msg)
        return -tmp2.real / (self.mn * self.r_s) + I_ph + I_0

    @classmethod
    def KXOB201K04F(cls, T_K: float | None = None) -> Self:
        if T_K is None:
            T_K = cls.T_stc
        T_suffix = f"_T{T_K:.0f}K"

        return cls(
            name=f"ANYSOLAR_KXOB201K04F{T_suffix}",
            I_SC_stc=83.8e-3,
            V_OC_stc=2.76,
            V_MP_stc=2.23,
            I_MP_stc=78.7e-3,
            n_s=4,
            dI_SCdt=37.9e-6,
            dV_OCdt=-6.96e-3,
            t=T_K,
        )


class MultivarRndWalk(EEnvGenerator):
    """
    I-V Surface generator that emulates a PV panel setup.

    Uses a multivariate random walk to determine open-circuit voltages for the different panels.
    Uses the given PV panel model to calculate terminal current at given terminal voltage. Applies
    a voltage ramp to generate surfaces.
    """

    def __init__(
        self,
        node_count: int,
        seed: int | None,
        V_OC_min: float,
        V_OC_max: float,
        correlation: float,
        variance: float,
        V_ramp_start: float,
        V_ramp_end: float,
        ramp_width: int,
        pv_model: SDMNoRP,
    ) -> None:
        super().__init__(
            datatype=EnergyDType.ivsurface, window_size=ramp_width, node_count=node_count, seed=seed
        )

        self.V_OC_min = V_OC_min
        self.V_OC_max = V_OC_max
        self.ramp_width = ramp_width
        self.V_ramp_start = V_ramp_start
        self.V_ramp_end = V_ramp_end
        self.mean = np.zeros(node_count)
        # Create a correlation matrix with off-diagonal values set to the correlation coefficient
        self.cov_matrix = self.gen_covariance_matrix(node_count, variance, correlation)
        self.pv: SDMNoRP = pv_model

        # Start pattern between the two bounds
        self.states = np.full(node_count, 0.5)
        self.ramp_offset = 0

    @staticmethod
    def gen_covariance_matrix(dim: int, variance: float, correlation: float) -> np.ndarray:
        """Generate a covariance matrix (dim x dim) with the given variance and correlation."""
        # Create a correlation matrix with off-diagonal values set to the correlation coefficient
        correlation_matrix = np.full((dim, dim), correlation)
        np.fill_diagonal(correlation_matrix, 1)  # Diagonal should be 1 (self-correlation)

        # Convert correlation matrix to covariance matrix using variance
        return correlation_matrix * variance

    def generate_random_pattern(self, count: int) -> np.ndarray:
        """Generate a random pattern in range(0, 1) using a multivariate random walk."""
        random = self.rnd_gen.multivariate_normal(self.mean, self.cov_matrix, size=count)
        walk = self.states + random.cumsum(axis=0)
        samples = np.clip(walk, min=0, max=1)
        self.states = samples[count - 1]

        return samples

    @staticmethod
    def generate_node_surface(
        params: tuple[SDMNoRP, np.ndarray, np.ndarray],
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generate an I-V surface from terminal voltages and O-C voltages."""
        (pv, Vs, V_OCs) = params
        cs = np.zeros(len(Vs))
        for j in range(len(Vs)):
            cs[j] = pv.get_i(V=Vs[j], V_OC=V_OCs[j])
        return Vs, cs

    def generate_iv_pairs(self, count: int) -> list[tuple[np.ndarray, np.ndarray]]:
        # Generate a single voltage ramp
        ramp = np.arange(
            self.V_ramp_start,
            self.V_ramp_end,
            (self.V_ramp_end - self.V_ramp_start) / self.ramp_width,
        )

        # Tile the ramp. Consider offset from previously generated values
        ramp_count = math.ceil((count + self.ramp_offset) / self.ramp_width)
        Vs = np.tile(ramp, ramp_count)

        # Truncate the voltage series according to the offset
        end = self.ramp_offset + count
        Vs = Vs[self.ramp_offset : self.ramp_offset + count]

        # Save the new ramp offset
        self.ramp_offset = end % self.ramp_width

        # Generate O-C voltage series. Generate pattern and scale to range(v_oc_min, v_oc_max)
        pattern = self.generate_random_pattern(count)
        V_OCs = self.V_OC_min + (self.V_OC_max - self.V_OC_min) * pattern

        # Generate current curves for the nodes in parallel
        pool = Pool(cpu_count())
        return pool.map(
            self.generate_node_surface,
            [(self.pv, Vs, V_OCs[::, i]) for i in range(self.node_count)],
        )


def get_worker_configs(
    params: Params = params_default,
) -> list[tuple[Callable, dict[str, Any]]]:
    """Generate worker-configurations for multivariate random walks.

    The config is a list of tuples. Each containing a
    callable function and a dict with its arguments.
    """
    cfgs: list[tuple[Callable, dict[str, Any]]] = []

    pv = SDMNoRP.KXOB201K04F()
    generator = MultivarRndWalk(
        node_count=params.node_count,
        seed=common_seed,
        correlation=0.9,
        variance=100e-12,
        V_OC_min=0.0,
        V_OC_max=3.5,
        V_ramp_start=0.0,
        V_ramp_end=5.0,
        ramp_width=909,
        pv_model=pv,
    )

    # Create output folder (or skip)
    folder_path = params.root_path / params.dir_name / f"solar_{pv.name}"
    # Check whether the output folder exists
    # Due to the multivariate generation method, nodes can not be generated
    # independently. Therefore, expanding an existing EEnv is not possible.
    if folder_path.exists():
        log.warning(
            "Folder %s exists. Skipping generation. "
            "(Generating nodes independently is not supported)",
            folder_path,
        )
        return cfgs

    node_paths = [folder_path / f"node{node_idx:03d}.h5" for node_idx in range(params.node_count)]
    args: dict[str, Any] = {
        "file_paths": node_paths,
        "duration": params.duration,
        "chunk_size": params.chunk_size,
    }
    cfgs.append((generator.generate_h5_files, args))
    return cfgs


def create_meta_data(params: Params = params_default) -> None:
    """Generate a YAML containing the metadata for the dataset.

    Combines data from hdf5-files itself and manually added descriptive data.
    """
    folder_path = params.root_path / params.dir_name
    name_ds = f"solar_{SDMNoRP.KXOB201K04F().name}"

    eprofiles: list[EnergyProfile] = []
    for node_idx in range(params.node_count):
        file_path = folder_path / name_ds / f"node{node_idx:03d}.h5"
        epro = EnergyProfile.derive_from_file(file_path)
        data_update = {
            # pretend data is available on server already (will be copied)
            "data_path": Path("/var/shepherd/content/eenv/nes_lab/")
            / file_path.relative_to(params.root_path),
            "data_2_copy": False,
        }
        eprofiles.append(epro.model_copy(deep=True, update=data_update))

    eenv = EnergyEnvironment(
        name=f"{params.dir_name}_solar",
        # TODO: deliberately not using {name_ds} to keep it short
        description=params.description,
        comment=f"created with {path_file.relative_to(path_file.parents[2])}",
        energy_profiles=eprofiles,
        owner="Ingmar",
        group="NES_Lab",
        visible2group=True,
        visible2all=True,
        metadata=params.metadata,
    )

    eenv_wrap = Wrapper(
        datatype=EnergyEnvironment.__name__,
        parameters=eenv.model_dump(exclude_none=True),
    )
    wraps_yaml = yaml.safe_dump(
        eenv_wrap.model_dump(exclude_unset=True, exclude_defaults=True),
        default_flow_style=False,
        sort_keys=False,
    )
    with (folder_path / f"_metadata_eenvs_{params.dir_name}.yaml").open("w") as f:
        f.write(wraps_yaml)


if __name__ == "__main__":
    process_sp(get_worker_configs())
    create_meta_data()
