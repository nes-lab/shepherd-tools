from typing import List
from typing import Optional

import numpy as np
from pydantic import Field
from pydantic import PositiveFloat
from pydantic import validate_call
from typing_extensions import Annotated

from .. import CalibrationCape
from .. import CalibrationEmulator
from .. import CalibrationHarvester
from .. import CalibrationPair
from .calibration import CapeData
from .shepherd import ShpModel

# TODO: move to shepherd_data to remove scipy-dependency from _core


class CalMeasurementPair(ShpModel):
    shepherd_raw: PositiveFloat
    reference_si: float = 0


CalMeasPairs = Annotated[List[CalMeasurementPair], Field(min_length=2)]


@validate_call
def meas_to_cal(data: CalMeasPairs, component: str) -> CalibrationPair:
    from scipy import stats  # here due to massive delay

    x = np.empty(len(data))
    y = np.empty(len(data))
    for i, pair in enumerate(data):
        x[i] = pair.shepherd_raw
        y[i] = pair.reference_si
    result = stats.linregress(x, y)
    offset = float(result.intercept)
    gain = float(result.slope)
    rval = result.rvalue  # test quality of regression

    if rval < 0.999:
        raise ValueError(
            "Calibration faulty -> Correlation coefficient "
            f"(rvalue) = {rval}:.6f is too low for '{component}'"
        )
    return CalibrationPair(offset=offset, gain=gain)


class CalMeasurementHarvester(ShpModel):
    dac_V_Hrv: CalMeasPairs
    dac_V_Sim: CalMeasPairs
    adc_V_Sense: CalMeasPairs
    adc_C_Hrv: CalMeasPairs

    def to_cal(self) -> CalibrationHarvester:
        dv = self.model_dump()
        dcal = CalibrationHarvester().model_dump()
        for key in dv:
            dcal[key] = meas_to_cal(self[key], f"hrv_{key}")
        return CalibrationHarvester(**dcal)


class CalMeasurementEmulator(ShpModel):
    dac_V_A: CalMeasPairs  # TODO: why not V_dac_A or V_dac_a
    dac_V_B: CalMeasPairs
    adc_C_A: CalMeasPairs
    adc_C_B: CalMeasPairs

    def to_cal(self) -> CalibrationEmulator:
        dv = self.model_dump()
        dcal = CalibrationEmulator().model_dump()
        for key in dv:
            dcal[key] = meas_to_cal(self[key], f"emu_{key}")
        return CalibrationEmulator(**dcal)


class CalMeasurementCape(ShpModel):
    cape: Optional[CapeData] = None
    host: Optional[str] = None

    harvester: Optional[CalMeasurementHarvester] = None
    emulator: Optional[CalMeasurementEmulator] = None

    def to_cal(self) -> CalibrationCape:
        dv = self.model_dump()
        dcal = CalibrationCape().model_dump()
        # TODO: is it helpful to default wrong / missing values?
        for key, value in dv.items():
            if key in {"harvester", "emulator"}:
                if value is not None:
                    dcal[key] = self[key].to_cal()
            else:
                dcal[key] = self[key]

        return CalibrationCape(**dcal)
