"""Generalized energy harvester data models."""

from collections.abc import Mapping
from enum import Enum
from typing import Annotated
from typing import Any
from typing import Optional

from pydantic import Field
from pydantic import model_validator
from typing_extensions import Self

from shepherd_core.config import config
from shepherd_core.data_models.base.calibration import CalibrationHarvester
from shepherd_core.data_models.base.content import ContentModel
from shepherd_core.data_models.base.shepherd import ShpModel
from shepherd_core.logger import log
from shepherd_core.testbed_client import tb_client

from .energy_environment import EnergyDType


class AlgorithmDType(str, Enum):
    """Options for choosing a harvesting algorithm."""

    direct = disable = neutral = "neutral"
    """
    Reads an energy environment as is without selecting a harvesting
    voltage.

    Used to play "constant-power" energy environments or simple
    "on-off-patterns". Generally, not useful for virtual source
    emulation.

    Not applicable to real harvesting, only emulation with IVTrace / samples.
    """

    isc_voc = "isc_voc"
    """
    Short Circuit Current, Open Circuit Voltage.

    This is not relevant for emulation, but used to configure recording of
    energy environments.

    This mode samples the two extremes of an IV curve, which may be
    interesting to characterize a transducer/energy environment.

    Not applicable to emulation - only recordable during harvest-recording ATM.
    """

    ivcurve = ivcurves = ivsurface = "ivcurve"
    """
    Used during harvesting to record the full IV surface.

    When configuring the energy environment recording, this algorithm
    records the IV surface by repeatedly recording voltage and current
    while ramping the voltage.

    Cannot be used as output of emulation.
    """

    constant = cv = "cv"
    """
    Harvest energy at a fixed predefined voltage ('voltage_mV').

    For harvesting, this records the IV samples at the specified voltage.
    For emulation, this virtually harvests the IV surface at the specified voltage.

    In addition to constant voltage harvesting, this can be used together
    with the 'feedback_to_hrv' flag to implement a "Capacitor and Diode"
    topology, where the harvesting voltage depends dynamically on the
    capacitor voltage.
    """

    # ci .. constant current -> is this desired?

    mppt_voc = "mppt_voc"
    """
    Emulate a harvester with maximum power point (MPP) tracking based on
    open circuit voltage measurements.

    This MPPT heuristic estimates the MPP as a constant ratio of the open
    circuit voltage.

    Used in conjunction with 'setpoint_n', 'interval_ms', and 'duration_ms'.
    """

    mppt_po = perturb_observe = "mppt_po"
    """
    Emulate a harvester with perturb and observe maximum power point
    tracking.

    This MPPT heuristic adjusts the harvesting voltage by small amounts and
    checks if the power increases. Eventually, the tracking changes the
    direction of adjustments and oscillates around the MPP.
    """

    mppt_opt = optimal = "mppt_opt"
    """
    A theoretical harvester that identifies the MPP by reading it from the
    IV curve during emulation.

    Note that this is not possible for real-world harvesting as the system would
    not know the entire IV curve. In that case a very fast and detailed mppt_po is
    used.
    """


class VirtualHarvesterConfig(ContentModel, title="Config for the Harvester"):
    """The virtual harvester configuration characterizes usage of an energy environment.

    It is used to both harvesting during emulation and to record
    energy environments (sometimes referred to as "harvesting traces").

    For emulation:

    The virtual harvester configuration describes how energy from a recorded
    energy environment is harvested. Typically, the energy environment provides
    an IV-surface, which is a continuous function in three dimensions: voltage,
    current, and time. Based on this surface, the emulation can derive the
    available IV-curve at each point in time. The harvester looks up the current
    that is available (according to the energy environment) from a given
    harvesting voltage. The harvesting voltage may be dynamically chosen by the
    harvester based on the implemented harvesting algorithm, which models
    different real-world harvesters. For example, a maximum power point tracking
    harvester may choose a harvesting voltage as a ratio of the open circuit
    voltage available from the energy environment (or transducer in practice).

    The energy environments are encoded not as a three-dimensional function, but
    as IV tuples over time (sampled at a constant frequency). This originates
    from the technical implementation when recording the IV-surface, where the
    recorder provides the IV-curve by measuring the current for a given voltage
    and ramping the voltage from minimal to maximum.

    For harvest-recordings:

    An energy environment is fully described by the IV surface, which are IV
    curves over time. Shepherd approximates this by sampling the current at
    equidistant steps of a voltage ramp. The VirtualHarvesterConfig is also used
    to parameterize the recording process, typically, it should be configured to
    record a full IV surface, as this contains the full information of the energy
    environment. The postponed harvesting is then performed during emulation.

    However, it is also possible to record a "pre-harvested" energy environment
    by performing the harvesting during recording. This results in a recording
    containing IV samples over time that represent the harvesting voltage
    (chosen by the virtual harvester during recording) and the current available
    from the energy environment for that voltage. Together, these represent the
    power available for harvesting at the time, and during emulation, this power
    can be converted by the input stage (boost converter) to charge the energy
    storage.
    """

    # General Metadata & Ownership -> ContentModel

    algorithm: AlgorithmDType
    """The algorithm determines how the harvester chooses the harvesting voltage.
    """

    samples_n: Annotated[int, Field(ge=8, le=2_000)] = 8
    """How many IV samples are measured for one IV curve.

    The curve is recorded by measuring the el. current available from the
    transducer at equidistant voltage intervals. These voltages are
    probed by ramping between `voltage_min_mV` and `voltage_max_mV` at
    `samples_n` points equally distributed over the voltage range. After
    setting the voltage, the recorder waits for a short period - allowing
    the analog frontend and transducer to settle - before recording the
    harvesting current. This wait duration is influenced by
    `wait_cycles`.

    Selecting all these parameters is a tradeoff between accuracy of the IV
    curve (density of IV samples) and measurement duration, hence the time
    accuracy (density of points) of the IV-surface.

    Only applicable to recording, not used in emulation.

    Used together with `voltage_min_mV`, `voltage_max_mV`, `rising`, and
    `wait_cycles`.
    """

    voltage_mV: Annotated[float, Field(ge=0, le=5_000)] = 2_500
    """The harvesting voltage for constant voltage harvesting.

    Additionally, for Perturb-and-Observe MPPT, this defines the voltage at
    startup.
    """

    voltage_min_mV: Annotated[float, Field(ge=0, le=5_000)] = 0
    """Minimum voltage recorded for the IV curve.

    See `samples_n` for further details.

    In emulation, this can be used to "block" parts of the recorded IV curve
    and not utilize them in the virtual source. However, this is generally
    discouraged as it can result in discontinuities in the curve and is not
    well tested.
    For emulation, this value ideally corresponds to the value of the
    recorded energy environment.
    """

    voltage_max_mV: Annotated[float, Field(ge=0, le=5_000)] = 5_000
    """Maximum voltage sampled for the curve.

    See `voltage_min_mV` and `samples_n`.
    """

    current_limit_uA: Annotated[float, Field(ge=1, le=50_000)] = 50_000
    """
    For MPPT VOC, the open circuit voltage is identified as the el. current
    crosses below this threshold.

    During recording it allows to keep trajectory in special region
    (constant current tracking).
    """

    voltage_step_mV: Optional[Annotated[float, Field(ge=1, le=1_000_000)]] = None
    """The difference between two adjacent voltage samples.

    This value is implicitly derived from the other ramp parameters:
    (voltage_max_mV - voltage_min_mV) / (samples_n - 1)
    """

    setpoint_n: Annotated[float, Field(ge=0, le=1.0)] = 0.70
    """
    The "Open Circuit Voltage Maximum Power Point Tracker" estimates the MPP
    by taking a constant fraction defined by this parameter of the open
    circuit voltage. For example, if the IV curve shows an open circuit
    voltage of 2V and the setpoint is 0.75, then the harvester selects
    1.5 volts as the harvesting voltage.

    This value is only relevant when 'algorithm == mppt_voc'.
    """

    interval_ms: Annotated[float, Field(ge=0.01, le=1_000_000)] = 100
    """The MPP is repeatedly estimated at fixed intervals defined by this duration.

    Note that the energy environment can still change in between MPP
    estimations, but the harvesting voltage is not updated in between.

    This value is relevant for all MPP algorithms.
    For Perturb and Observe, this value is the wait interval between steps.

    When an energy environment is recorded with `mppt_opt`, the optimal
    harvester is approximated with a very fast Perturb-Observe algorithm,
    where this interval should be set to a very small value.
    When emulating with `mppt_opt`, this value is not relevant as the
    emulation simply picks the maximum power point from the IV-curve.
    """

    duration_ms: Annotated[float, Field(ge=0.01, le=1_000_000)] = 0.1
    """The duration of MPP sampling.

    While performing an MPP sampling every 'interval_ms', the input is
    disconnected to accurately measure the open circuit voltage.

    This value is only relevant for `mppt_voc`.
    """

    rising: bool = True
    """Ramp direction for sampling the IV curve.

    When set to true, sampling starts at the minimum voltage and ramps up to
    the maximum.

    See `samples_n` for further details.
    Not relevant for emulation.
    """

    enable_linear_extrapolation: bool = True
    """
    Because the IV curve is not stored fully in PRU memory but streamed
    sequentially to the PRU, looking up any IV value at any time is not
    possible. However, because the precision of the emulation degrades
    until the relevant IV sample passes by, it can extrapolate the available data
    to estimate the required IV sample.

    Enabling extrapolation can yield a better numeric simulation, especially
    if the harvesting voltage changes rapidly or the IV surface is steep in
    relevant regions. For example, when emulating a capacitor diode
    setup and the current falls at high voltages.

    This value is only relevant for emulation.
    """

    # Underlying recorder
    wait_cycles: Annotated[int, Field(ge=0, le=100)] = 1
    """
    The wait duration to let the analog frontend settle before taking a
    measurement.

    When recording the energy environment, the voltage is set by the
    digital-to-analog-converter. This parameter delays the current
    measurement performed by the analog-to-digital converter to allow the
    harvesting transducer to settle at the defined voltage.

    When recording with `IscVoc`, wait cycles should be added as the analog
    changes are more significant.

    Not relevant for emulation.
    """

    # ⤷ first cycle: ADC-Sampling & DAC-Writing, further steps: waiting

    @model_validator(mode="before")
    @classmethod
    def query_database(cls, values: dict[str, Any]) -> dict[str, Any]:
        values, chain = tb_client.try_completing_model(cls.__name__, values)
        values = tb_client.fill_in_user_data(values)
        if values["name"] == "neutral":
            # TODO: same test is later done in calc_algorithm_num() again
            raise ValueError("Resulting Harvester can't be neutral")
        log.debug("VHrv-Inheritances: %s", chain)

        # post corrections -> should be in separate validator
        cal = CalibrationHarvester()  # TODO: as argument?
        c_limit = values.get("current_limit_uA", 50_000)  # cls.current_limit_uA)
        values["current_limit_uA"] = max(10**6 * cal.adc_C_Hrv.raw_to_si(4), c_limit)

        if values.get("voltage_step_mV") is None:
            # algo includes min & max!
            v_max = values.get("voltage_max_mV", 5_000)  # cls.voltage_max_mV)
            v_min = values.get("voltage_min_mV", 0)  # cls.voltage_min_mV)
            samples_n = values.get("samples_n", 8)  # cls.samples_n) TODO
            values["voltage_step_mV"] = abs(v_max - v_min) / (samples_n - 1)

        values["voltage_step_mV"] = max(
            10**3 * cal.dac_V_Hrv.raw_to_si(4), values["voltage_step_mV"]
        )

        return values

    @model_validator(mode="after")
    def post_validation(self) -> Self:
        if self.voltage_min_mV > self.voltage_max_mV:
            raise ValueError("Voltage min > max")
        if self.voltage_mV < self.voltage_min_mV:
            raise ValueError("Voltage below min")
        if self.voltage_mV > self.voltage_max_mV:
            raise ValueError("Voltage above max")

        return self

    def calc_hrv_mode(self, *, for_emu: bool) -> int:
        return 1 * int(for_emu) + 2 * self.rising + 4 * self.enable_linear_extrapolation

    def calc_algorithm_num(self, *, for_emu: bool) -> int:
        num: int = ALGO_TO_NUM.get(self.algorithm, ALGO_TO_NUM["neutral"])
        if for_emu and self.get_datatype() != EnergyDType.ivsample:
            msg = (
                f"[{self.name}] Select valid harvest-algorithm for emulator, "
                f"current usage = {self.algorithm}"
            )
            raise ValueError(msg)
        if not for_emu and num < ALGO_TO_NUM["isc_voc"]:
            msg = (
                f"[{self.name}] Select valid harvest-algorithm for harvester, "
                f"current usage = {self.algorithm}"
            )
            raise ValueError(msg)
        return num

    def calc_timings_ms(self, *, for_emu: bool) -> tuple[float, float]:
        """factor-in model-internal timing-constraints."""
        window_length = self.samples_n * (1 + self.wait_cycles)
        time_min_ms = (1 + self.wait_cycles) * 1_000 / config.SAMPLERATE_SPS
        if for_emu:
            window_ms = window_length * 1_000 / config.SAMPLERATE_SPS
            time_min_ms = max(time_min_ms, window_ms)

        interval_ms = min(max(self.interval_ms, time_min_ms), 1_000_000)
        duration_ms = min(max(self.duration_ms, time_min_ms), interval_ms)
        _ratio = (duration_ms / interval_ms) / (self.duration_ms / self.interval_ms)
        if (_ratio - 1) > 0.1:
            log.debug(
                "Ratio between interval & duration has changed "
                "more than 10%% due to constraints (%.4f)",
                _ratio,
            )
        return interval_ms, duration_ms

    def get_datatype(self) -> EnergyDType:
        return ALGO_TO_DTYPE[self.algorithm]

    def calc_window_size(
        self,
        dtype_in: Optional[EnergyDType] = None,
        *,
        for_emu: bool,
    ) -> int:
        if not for_emu:
            # TODO: should be named 'for_ivcurve_recording'
            # TODO: add extra variable to distinguish step_count
            #       and window_size (currently mixed together)
            # only used by ivcurve algo (in ADC-Mode)
            return self.samples_n

        if dtype_in is None:
            dtype_in = self.get_datatype()

        if dtype_in == EnergyDType.ivcurve:
            return self.samples_n * (1 + self.wait_cycles)
        if dtype_in == EnergyDType.ivsample:
            return 0
        if dtype_in == EnergyDType.isc_voc:
            return 2 * (1 + self.wait_cycles)
        raise NotImplementedError


u32 = Annotated[int, Field(ge=0, lt=2**32)]


# Currently implemented harvesters
# NOTE: numbers have meaning and will be tested ->
# - harvesting on "neutral" is not possible - direct pass-through
# - emulation with "ivcurve" or lower is also resulting in Error
# - "_opt" has its own algo for emulation, but is only a fast mppt_po for harvesting
ALGO_TO_NUM: Mapping[str, int] = {
    "neutral": 2**0,
    "isc_voc": 2**3,
    "ivcurve": 2**4,
    "cv": 2**8,
    # is "ci" desired?
    "mppt_voc": 2**12,
    "mppt_po": 2**13,
    "mppt_opt": 2**14,
}

ALGO_TO_DTYPE: Mapping[str, EnergyDType] = {
    "neutral": EnergyDType.ivsample,
    "isc_voc": EnergyDType.isc_voc,
    "ivcurve": EnergyDType.ivcurve,
    "cv": EnergyDType.ivsample,
    "mppt_voc": EnergyDType.ivsample,
    "mppt_po": EnergyDType.ivsample,
    "mppt_opt": EnergyDType.ivsample,
}


class HarvesterPRUConfig(ShpModel):
    """Map settings-list to internal state-vars struct HarvesterConfig for PRU.

    NOTE:
      - yaml is based on si-units like nA, mV, ms, uF
      - c-code and py-copy is using nA, uV, ns, nF, fW, raw
      - ordering is intentional and in sync with shepherd/commons.h.
    """

    algorithm: u32
    hrv_mode: u32
    window_size: u32
    voltage_uV: u32
    voltage_min_uV: u32
    voltage_max_uV: u32
    voltage_step_uV: u32
    """ ⤷ for window-based algo like ivcurve"""
    current_limit_nA: u32
    """ ⤷ lower bound to detect zero current"""
    setpoint_n8: u32
    interval_n: u32
    """ ⤷ between measurements"""
    duration_n: u32
    """ ⤷ of measurement"""
    wait_cycles_n: u32
    """ ⤷ for DAC to settle"""

    @classmethod
    def from_vhrv(
        cls,
        data: VirtualHarvesterConfig,
        dtype_in: Optional[EnergyDType] = EnergyDType.ivsample,
        window_size: Optional[u32] = None,
        voltage_step_V: Optional[float] = None,
        *,
        for_emu: bool = False,
    ) -> Self:
        if isinstance(dtype_in, str):
            dtype_in = EnergyDType[dtype_in]
        if for_emu and dtype_in not in {EnergyDType.ivsample, EnergyDType.ivcurve}:
            raise NotImplementedError

        if for_emu and dtype_in == EnergyDType.ivcurve and voltage_step_V is None:
            raise ValueError(
                "For correct emulation specify voltage_step used by harvester "
                "e.g. via file_src.get_voltage_step()"
            )

        if for_emu and dtype_in == EnergyDType.ivcurve and window_size is None:
            raise ValueError(
                "For correct emulation specify window_size used by harvester "
                "e.g. via file_src.get_window_size()"
            )

        interval_ms, duration_ms = data.calc_timings_ms(for_emu=for_emu)
        window_size = (
            window_size
            if window_size is not None
            else data.calc_window_size(dtype_in, for_emu=for_emu)
        )
        if voltage_step_V is not None:
            voltage_step_mV = 1e3 * voltage_step_V
        elif data.voltage_step_mV is not None:
            voltage_step_mV = data.voltage_step_mV
        else:
            raise ValueError(
                "For correct emulation specify voltage_step used by harvester "
                "e.g. via file_src.get_voltage_step()"
            )

        return cls(
            algorithm=data.calc_algorithm_num(for_emu=for_emu),
            hrv_mode=data.calc_hrv_mode(for_emu=for_emu),
            window_size=window_size,
            voltage_uV=round(data.voltage_mV * 10**3),
            voltage_min_uV=round(data.voltage_min_mV * 10**3),
            voltage_max_uV=round(data.voltage_max_mV * 10**3),
            voltage_step_uV=round(voltage_step_mV * 10**3),
            current_limit_nA=round(data.current_limit_uA * 10**3),
            setpoint_n8=round(min(255, data.setpoint_n * 2**8)),
            interval_n=round(interval_ms * config.SAMPLERATE_SPS * 1e-3),
            duration_n=round(duration_ms * config.SAMPLERATE_SPS * 1e-3),
            wait_cycles_n=data.wait_cycles,
        )
