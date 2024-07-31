"""parametrized math models for converting between raw- and si-values.

Contains some info about the hardware configuration on the shepherd
cape. Based on these values, one can derive the expected adc readings given
an input voltage/current or, for emulation, the expected voltage and current
given the digital code in the DAC.

currently configured for cape v2.4c

"""

# both current channels have a 0.1 % shunt resistance of
R_SHT = 2.0  # [ohm]
# the instrumentation amplifiers are configured for gain of
G_INST_AMP = 48  # [n]
# we use the ADC's internal reference with
V_REF_ADC = 4.096  # [V]
# range of current channels is
G_ADC_I = 1.25  # [gain / V_REF]
# range of voltage channels is
G_ADC_V = 1.25  # [gain / V_REF]
# bit resolution of ADC
M_ADC = 18  # [bit]
# DACs use internal reference with
V_REF_DAC = 2.5  # [V]
# gain of DAC is set to
G_DAC = 2  # [n]
# bit resolution of DAC
M_DAC = 16  # [bit]
# DERIVED VARIABLES
RAW_MAX_ADC = 2**M_ADC - 1
RAW_MAX_DAC = 2**M_DAC - 1


def adc_current_to_raw(current: float, *, limited: bool = True) -> int:
    """Convert back a current [A] to raw ADC value."""
    # voltage on input of adc
    val_adc = G_INST_AMP * R_SHT * current
    # digital value according to ADC gain
    val_raw = int(val_adc * (2**M_ADC) / (G_ADC_I * V_REF_ADC))
    return min(max(val_raw, 0), 2**M_ADC - 1) if limited else val_raw


def adc_raw_to_current(value: int, *, limited: bool = True) -> float:
    """Convert a raw ADC value to a current [A]."""
    if limited:
        value = min(max(value, 0), 2**M_ADC - 1)
    # voltage on input of adc
    val_adc = float(value) * (G_ADC_I * V_REF_ADC) / (2**M_ADC)
    # current according to adc value
    return val_adc / (R_SHT * G_INST_AMP)


def adc_voltage_to_raw(voltage: float, *, limited: bool = True) -> int:
    """Convert back a voltage [V] to raw ADC value."""
    # digital value according to ADC gain
    val_raw = int(voltage * (2**M_ADC) / (G_ADC_V * V_REF_ADC))
    return min(max(val_raw, 0), 2**M_ADC - 1) if limited else val_raw


def adc_raw_to_voltage(value: int, *, limited: bool = True) -> float:
    """Convert a raw ADC value to a voltage [V]."""
    if limited:
        value = min(max(value, 0), 2**M_ADC - 1)
    # voltage according to ADC value
    return float(value) * (G_ADC_V * V_REF_ADC) / (2**M_ADC)


def dac_raw_to_voltage(value: int, *, limited: bool = True) -> float:
    """Convert back a raw DAC value to a voltage [V]."""
    if limited:
        value = min(max(value, 0), 2**M_DAC - 1)
    return float(value) * (V_REF_DAC * G_DAC) / (2**M_DAC)


def dac_voltage_to_raw(voltage: float, *, limited: bool = True) -> int:
    """Convert a voltage [V] to raw DAC value."""
    val_raw = int(voltage * (2**M_DAC) / (V_REF_DAC * G_DAC))
    return min(max(val_raw, 0), 2**M_DAC - 1) if limited else val_raw
