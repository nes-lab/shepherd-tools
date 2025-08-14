"""I-V Surface generation script for a multivariate random walk of sample PV panels."""

import math
import shutil
import sys
from multiprocessing import Pool
from multiprocessing import cpu_count
from pathlib import Path
from typing import Self

import numpy as np
from commons import EEnvGenerator
from scipy.optimize import newton
from scipy.special import lambertw

from shepherd_core.data_models import EnergyDType
from shepherd_core.logger import log

# Constants
k = 1.380649e-23  # Boltzmann constant
q = 1.602176634e-19  # Elementary charge
t_stc = 25 + 273.15  # 25 C in Kelvin
g_stc = 1000  # W/m2


class SDMNoRPCurve:
    """I(V) function of the single-diode-model with series resistance."""

    def __init__(self, i_ph: float, i_0: float, r_s: float, n: float, n_s: int, t: float) -> None:
        self.i_ph = i_ph
        self.i_0 = i_0
        self.r_s = r_s
        self.mn = q / (n_s * k * t * n)

    def get_i(self, v: float) -> float:
        """
        Compute I(V) using the Lambert-W function.

        Original SDM Equation:
            i = i_pv - i_0 * (exp(mn * (v + i * r_s)) - 1)
        where:
            mn = q / (n_s * k * t * n)

        Conditions:
            i_0 != 0; otherwise the diodes in the SDM becomes meaningless
            mn != 0; true since q != 0
            r_s != 0; otherwise we have SDM without series resistance
        """
        tmp1 = (
            self.i_0
            * self.mn
            * self.r_s
            * math.exp(self.mn * (self.i_ph * self.r_s + self.i_0 * self.r_s + v))
        )

        tmp2 = lambertw(tmp1)
        if tmp2.imag != 0:
            msg = f"Lambert-W result is not a real number: W({tmp1}) = {tmp2}"
            raise RuntimeError(msg)

        return -tmp2.real / (self.mn * self.r_s) + self.i_ph + self.i_0


class SDMNoRP:
    """
    Single diode model using datasheet parameters.

    See: https://doi.org/10.1109/ICIINFS.2011.6038128
    """

    def __init__(
        self,
        name: str,
        i_sc_stc: float,
        v_oc_stc: float,
        v_mp_stc: float,
        i_mp_stc: float,
        n_s: int,
        di_scdt: float,
        dv_ocdt: float,
    ) -> None:
        self.name = name
        self.i_sc_stc = i_sc_stc
        self.v_oc_stc = v_oc_stc
        self.v_mp_stc = v_mp_stc
        self.i_mp_stc = i_mp_stc
        self.n_s = n_s
        self.di_scdt = di_scdt
        self.dv_ocdt = dv_ocdt

        m_stc = q / (n_s * k * t_stc)
        self.m_stc = m_stc

        def f(n: float) -> float:
            # Equation 6
            i_0_stc = i_sc_stc / (math.exp(m_stc * v_oc_stc / n) - 1)
            # Equation 18
            return n * i_mp_stc + (i_sc_stc - i_mp_stc + i_0_stc) * (
                n * math.log((i_sc_stc - i_mp_stc + i_0_stc) / i_0_stc) - 2 * m_stc * v_mp_stc
            )

        def df(n: float) -> float:
            # Equation 6
            i_0_stc = i_sc_stc / (math.exp(m_stc * v_oc_stc / n) - 1)
            # Equation 20
            di_0dn = (
                m_stc
                * v_oc_stc
                * i_sc_stc
                * math.exp(m_stc * v_oc_stc / n)
                / (n**2 * (math.exp(m_stc * v_oc_stc / n) - 1) ** 2)
            )
            # Equation 19
            return (
                i_mp_stc
                + di_0dn
                * (n * math.log((i_sc_stc - i_mp_stc + i_0_stc) / i_0_stc) - 2 * m_stc * v_mp_stc)
                + (
                    i_sc_stc
                    - i_mp_stc
                    + i_0_stc
                    * (
                        math.log((i_sc_stc - i_mp_stc + i_0_stc) / i_0_stc)
                        - n
                        * (i_sc_stc - i_mp_stc)
                        / ((i_sc_stc - i_mp_stc + i_0_stc) * i_0_stc)
                        * di_0dn
                    )
                )
            )

        # Equation 22
        self.n = newton(func=f, fprime=df, x0=1, tol=1e-3, maxiter=10000)

    def get_g(self, v_oc: float, t: float) -> float:
        return g_stc * math.exp(
            (v_oc - self.v_oc_stc - self.dv_ocdt * (t - t_stc)) * q / (t * self.n * self.n_s * k)
        )

    def get_iv(self, g: float, t: float) -> dict:
        # Equation 2
        m = q / (self.n_s * k * t)

        # Equation 4
        i_sc = self.i_sc_stc * g / g_stc * (1 + self.di_scdt * (t - t_stc))

        # Equation 5
        v_oc = self.v_oc_stc + self.dv_ocdt * (t - t_stc) + self.n / m * math.log(g / g_stc)

        # Equation 3
        i_ph = i_sc

        # Equation 6
        i_0 = i_sc / (math.exp(m * v_oc / self.n) - 1)
        i_0_stc = self.i_sc_stc / (math.exp(self.m_stc * self.v_oc_stc / self.n) - 1)

        # Equation 8
        r_s = (
            self.n
            / (self.m_stc * self.i_mp_stc)
            * math.log((self.i_sc_stc - self.i_mp_stc + i_0_stc) / i_0_stc)
            - self.v_mp_stc / self.i_mp_stc
        )

        return SDMNoRPCurve(i_ph=i_ph, i_0=i_0, r_s=r_s, n=self.n, n_s=self.n_s, t=t)

    def get_i(self, v: float, v_oc: float, t: float = t_stc) -> float:
        g = self.get_g(v_oc=v_oc, t=t)
        curve = self.get_iv(g=g, t=t)
        return curve.get_i(v)

    @classmethod
    def KXOB201K04F(cls: Self) -> Self:
        return cls(
            name="ANYSOLAR_KXOB201K04F",
            i_sc_stc=83.8e-3,
            v_oc_stc=2.76,
            v_mp_stc=2.23,
            i_mp_stc=78.7e-3,
            n_s=4,
            di_scdt=37.9e-6,
            dv_ocdt=-6.96e-3,
        )


class MultivarRndWalk(EEnvGenerator):
    """
    I-V Surface generator that emulates a PV panel setup.

    Uses a multivariate random walk to determine open-circuit voltages for the different panels.
    Uses the given PV panel model to calculate terminal current given terminal voltage. Applies
    a voltage ramp to generate surfaces.
    """

    def __init__(
        self,
        node_count: int,
        seed: int | None,
        v_oc_min: float,
        v_oc_max: float,
        correlation: float,
        variance: float,
        v_ramp_start: float,
        v_ramp_end: int,
        ramp_width: int,
        pv_model: SDMNoRP,
    ) -> None:
        super().__init__(
            datatype=EnergyDType.ivsurface, window_size=ramp_width, node_count=node_count, seed=seed
        )

        self.v_oc_min = v_oc_min
        self.v_oc_max = v_oc_max
        self.ramp_width = ramp_width
        self.v_ramp_start = v_ramp_start
        self.v_ramp_end = v_ramp_end
        self.mean = np.zeros(node_count)
        # Create a correlation matrix with off-diagonal values set to the correlation coefficient
        self.cov_matrix = self.gen_covariance_matrix(node_count, variance, correlation)
        self.pv = pv_model

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
        params: tuple[np.ndarray, np.ndarray, np.ndarray],
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generate an I-V surface from terminal voltages and O-C voltages."""
        (pv, vs, v_ocs) = params
        cs = np.zeros(len(vs))
        for j in range(len(vs)):
            cs[j] = pv.get_i(v=vs[j], v_oc=v_ocs[j], t=300)  # TODO: fixed T here
        return (vs, cs)

    def generate_iv_pairs(self, count: int) -> list[tuple[np.ndarray, np.ndarray]]:
        # Generate a single voltage ramp
        ramp = np.arange(
            self.v_ramp_start,
            self.v_ramp_end,
            (self.v_ramp_end - self.v_ramp_start) / self.ramp_width,
        )

        # Tile the ramp. Consider offset from previously generated values
        ramp_count = math.ceil((count + self.ramp_offset) / self.ramp_width)
        vs = np.tile(ramp, ramp_count)

        # Truncate the voltage series according to the offset
        end = self.ramp_offset + count
        vs = vs[self.ramp_offset : self.ramp_offset + count]

        # Save the new ramp offset
        self.ramp_offset = end % self.ramp_width

        # Generate O-C voltage series. Generate pattern and scale to range(v_oc_min, v_oc_max)
        pattern = self.generate_random_pattern(count)
        v_ocs = self.v_oc_min + (self.v_oc_max - self.v_oc_min) * pattern

        # Generate current curves for the nodes in parallel
        pool = Pool(cpu_count())
        return pool.map(
            self.generate_node_surface,
            [(self.pv, vs, v_ocs[::, i]) for i in range(self.node_count)],
        )


if __name__ == "__main__":
    path_here = Path(__file__).parent.absolute()
    if Path("/var/shepherd/").exists():
        path_eenv = Path("/var/shepherd/content/eenv/nes_lab/")
    else:
        path_eenv = path_here / "content/eenv/nes_lab/"

    node_count = 20
    seed = 32220789340897324098232347119065234157809
    duration = 4 * 60 * 60.0

    pv = SDMNoRP.KXOB201K04F()
    generator = MultivarRndWalk(
        node_count=node_count,
        seed=seed,
        correlation=0.9,
        variance=100e-12,
        v_oc_min=0.0,
        v_oc_max=3.5,
        v_ramp_start=0.0,
        v_ramp_end=5.0,
        ramp_width=909,
        pv_model=pv,
    )

    # Create output folder (or skip)
    name = f"artificial_solar_multivariate_random_{pv.name}"
    folder_path = path_eenv / name
    # Check whether the output folder exists
    # Due to the multivariate generation method, nodes can not be generated
    # independently. Therefore expanding an existing EEnv is not possible.
    if folder_path.exists():
        log.info(
            "Folder %s exists. Skipping generation. "
            "(Generating nodes independently is not supported)",
            folder_path,
        )
        sys.exit(1)

    try:
        folder_path.mkdir(parents=True, exist_ok=False)
        node_paths = [folder_path / f"node{node_idx}.h5" for node_idx in range(node_count)]

        generator.generate_h5_files(node_paths, duration=duration, chunk_size=1_000_000)
    except:
        log.error("Exception encountered. Removing incomplete dataset: %s", folder_path)
        shutil.rmtree(folder_path)
        raise
