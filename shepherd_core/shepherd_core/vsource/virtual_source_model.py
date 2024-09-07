"""This is ported py-version of the pru-code.

Goals:

- stay close to original code-base
- offer a comparison for the tests
- step 1 to a virtualization of emulation.

NOTE: DO NOT OPTIMIZE -> stay close to original code-base

"""

from typing import Optional

from ..data_models import CalibrationEmulator
from ..data_models import EnergyDType
from ..data_models import VirtualSourceConfig
from ..data_models.content.virtual_harvester import HarvesterPRUConfig
from ..data_models.content.virtual_source import ConverterPRUConfig
from .virtual_converter_model import PruCalibration
from .virtual_converter_model import VirtualConverterModel
from .virtual_harvester_model import VirtualHarvesterModel


class VirtualSourceModel:
    """part of sampling.c."""

    def __init__(
        self,
        vsrc: Optional[VirtualSourceConfig],
        cal_emu: CalibrationEmulator,
        dtype_in: EnergyDType = EnergyDType.ivsample,
        window_size: Optional[int] = None,
        *,
        log_intermediate: bool = False,
    ) -> None:
        self._cal_emu: CalibrationEmulator = cal_emu
        self._cal_pru: PruCalibration = PruCalibration(cal_emu)

        self.cfg_src = VirtualSourceConfig() if vsrc is None else vsrc
        cnv_config = ConverterPRUConfig.from_vsrc(
            self.cfg_src,
            dtype_in=dtype_in,
            log_intermediate_node=log_intermediate,
        )
        self.cnv: VirtualConverterModel = VirtualConverterModel(cnv_config, self._cal_pru)

        hrv_config = HarvesterPRUConfig.from_vhrv(
            self.cfg_src.harvester,
            for_emu=True,
            dtype_in=dtype_in,
            window_size=window_size,
        )

        self.hrv: VirtualHarvesterModel = VirtualHarvesterModel(hrv_config)

        self.W_inp_fWs: float = 0.0
        self.W_out_fWs: float = 0.0

    def iterate_sampling(self, V_inp_uV: int = 0, I_inp_nA: int = 0, I_out_nA: int = 0) -> int:
        """TEST-SIMPLIFICATION - code below is not part of pru-code.

        It originates from sample_emulator() in sampling.c.

        :param V_inp_uV:
        :param I_inp_nA:
        :param I_out_nA:
        :return:
        """
        V_inp_uV, I_inp_nA = self.hrv.ivcurve_sample(V_inp_uV, I_inp_nA)

        P_inp_fW = self.cnv.calc_inp_power(V_inp_uV, I_inp_nA)

        # fake ADC read
        A_out_raw = self._cal_emu.adc_C_A.si_to_raw(I_out_nA * 10**-9)

        P_out_fW = self.cnv.calc_out_power(A_out_raw)
        V_mid_uV = self.cnv.update_cap_storage()
        V_out_raw = self.cnv.update_states_and_output()
        V_out_uV = int(self._cal_emu.dac_V_A.raw_to_si(V_out_raw) * 10**6)

        self.W_inp_fWs += P_inp_fW
        self.W_out_fWs += P_out_fW

        # feedback path - important for boost-less circuits
        if self.cnv.feedback_to_hrv:
            self.hrv.voltage_set_uV = self.cnv.V_input_request_uV

        return V_mid_uV if self.cnv.get_state_log_intermediate() else V_out_uV
