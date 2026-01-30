"""Separated data-type.

Done due to cyclic inheritance.
"""

from enum import Enum


class EnergyDType(str, Enum):
    """Data-Type-Options for energy environments."""

    ivtrace = ivsample = ivsamples = "ivsample"
    ivsurface = ivcurve = ivcurves = "ivcurve"
    isc_voc = "isc_voc"


class FirmwareDType(str, Enum):
    """Options for firmware-types."""

    base64_hex = "hex"
    base64_elf = "elf"
    path_hex = "path_hex"
    path_elf = "path_elf"


class HarvestAlgorithmDType(str, Enum):
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
