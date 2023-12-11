"""this is ported py-version of the pru-code, goals:
- stay close to original code-base
- offer a comparison for the tests
- step 1 to a virtualization of emulation

NOTE1: DO NOT OPTIMIZE -> stay close to original c-code-base
NOTE2: adc-harvest-routines are not part of this model (virtual_harvester lines 66:289)

Compromises:
- Py has to map the settings-list to internal vars -> is kernel-task
- Python has no static vars -> FName_reset is handling the class-vars

"""
from typing import Tuple

from ..data_models.content.virtual_harvester import HarvesterPRUConfig


class VirtualHarvesterModel:
    HRV_IVCURVE: int = 2**4
    HRV_CV: int = 2**8
    HRV_MPPT_VOC: int = 2**12
    HRV_MPPT_PO: int = 2**13
    HRV_MPPT_OPT: int = 2**14

    def __init__(self, cfg: HarvesterPRUConfig) -> None:
        self._cfg: HarvesterPRUConfig = cfg

        # INIT global vars: shared states
        self.voltage_set_uV: int = self._cfg.voltage_uV + 1
        self.interval_step: int = 2**30
        self.is_rising: bool = (self._cfg.hrv_mode & (2**1)) != 0

        # PO-Relevant, iv & adc
        self.volt_step_uV: int = self._cfg.voltage_step_uV

        # adc_ivcurve
        # self.settle_steps: int = 0  # noqa: ERA001

        # adc_mppt_po
        # self.power_last_raw: int = 0 # noqa: ERA001

        # globals for iv_cv
        self.voltage_hold: int = 0
        self.current_hold: int = 0
        self.voltage_step_x4_uV: int = self._cfg.voltage_step_uV * 4

        # INIT static vars: CV
        self.voltage_last: int = 0
        self.current_last: int = 0
        self.compare_last: int = 0

        # INIT static vars: VOC
        self.age_now: int = 0
        self.voc_now: int = 0
        self.age_nxt: int = 0
        self.voc_nxt: int = 0

        # INIT static vars: PO
        # already done: interval step
        self.power_last: int = 0

        # INIT static vars: OPT
        # already done: age_now, age_nxt
        self.power_now: int = 0
        self.voltage_now: int = 0
        self.current_now: int = 0
        self.power_nxt: int = 0
        self.voltage_nxt: int = 0
        self.current_nxt: int = 0

    def ivcurve_sample(self, _voltage_uV: int, _current_nA: int) -> Tuple[int, int]:
        if self._cfg.window_size <= 1:
            return _voltage_uV, _current_nA
        if self._cfg.algorithm >= self.HRV_MPPT_OPT:
            return self.ivcurve_2_mppt_opt(_voltage_uV, _current_nA)
        if self._cfg.algorithm >= self.HRV_MPPT_PO:
            return self.ivcurve_2_mppt_po(_voltage_uV, _current_nA)
        if self._cfg.algorithm >= self.HRV_MPPT_VOC:
            return self.ivcurve_2_mppt_voc(_voltage_uV, _current_nA)
        if self._cfg.algorithm >= self.HRV_CV:
            return self.ivcurve_2_cv(_voltage_uV, _current_nA)
        # next line is only implied in C
        return _voltage_uV, _current_nA

    def ivcurve_2_cv(self, _voltage_uV: int, _current_nA: int) -> Tuple[int, int]:
        compare_now = _voltage_uV < self.voltage_set_uV
        step_size_now = abs(_voltage_uV - self.voltage_last)
        distance_now = abs(_voltage_uV - self.voltage_set_uV)
        distance_last = abs(self.voltage_last - self.voltage_set_uV)

        if compare_now != self.compare_last and step_size_now < self.voltage_step_x4_uV:
            if distance_now < distance_last and distance_now < self.voltage_step_x4_uV:
                self.voltage_hold = _voltage_uV
                self.current_hold = _current_nA
            elif distance_last < distance_now and distance_last < self.voltage_step_x4_uV:
                self.voltage_hold = self.voltage_last
                self.current_hold = self.current_last

        self.voltage_last = _voltage_uV
        self.current_last = _current_nA
        self.compare_last = compare_now
        return self.voltage_hold, self.current_hold

    def ivcurve_2_mppt_voc(self, _voltage_uV: int, _current_nA: int) -> Tuple[int, int]:
        self.interval_step = (self.interval_step + 1) % self._cfg.interval_n
        self.age_nxt += 1
        self.age_now += 1

        if (
            (_current_nA < self._cfg.current_limit_nA)
            and (_voltage_uV < self.voc_nxt)
            and (_voltage_uV >= self._cfg.voltage_min_uV)
            and (_voltage_uV <= self._cfg.voltage_max_uV)
        ):
            self.voc_nxt = _voltage_uV
            self.age_nxt = 0

        if (self.age_now > self._cfg.window_size) or (self.voc_nxt <= self.voc_now):
            self.age_now = self.age_nxt
            self.voc_now = self.voc_nxt
            self.age_nxt = 0
            self.voc_nxt = self._cfg.voltage_max_uV

        _voltage_uV, _current_nA = self.ivcurve_2_cv(_voltage_uV, _current_nA)
        if self.interval_step < self._cfg.duration_n:
            self.voltage_set_uV = int(self.voc_now * self._cfg.setpoint_n8 / 256)
            _current_nA = 0

        return _voltage_uV, _current_nA

    def ivcurve_2_mppt_po(self, _voltage_uV: int, _current_nA: int) -> Tuple[int, int]:
        self.interval_step = (self.interval_step + 1) % self._cfg.interval_n

        _voltage_uV, _current_nA = self.ivcurve_2_cv(_voltage_uV, _current_nA)

        if self.interval_step == 0:
            power_now = _voltage_uV * _current_nA
            if power_now > self.power_last:
                if self.is_rising:
                    self.voltage_set_uV += self.volt_step_uV
                else:
                    self.voltage_set_uV -= self.volt_step_uV
                self.volt_step_uV *= 2
            elif (power_now <= 0) and (self.voltage_set_uV > 0):
                self.is_rising = True
                self.volt_step_uV = self._cfg.voltage_step_uV
                self.voltage_set_uV -= self.voltage_step_x4_uV
            else:
                self.is_rising = not self.is_rising
                self.volt_step_uV = self._cfg.voltage_step_uV
                if self.is_rising:
                    self.voltage_set_uV += self.volt_step_uV
                else:
                    self.voltage_set_uV -= self.volt_step_uV

            self.power_last = power_now

            if self.voltage_set_uV >= self._cfg.voltage_max_uV:
                self.voltage_set_uV = self._cfg.voltage_max_uV
                self.is_rising = False
                self.volt_step_uV = self._cfg.voltage_step_uV
            if self.voltage_set_uV <= self._cfg.voltage_min_uV:
                self.voltage_set_uV = self._cfg.voltage_min_uV
                self.is_rising = True
                self.volt_step_uV = self._cfg.voltage_step_uV
            if self.voltage_set_uV <= self._cfg.voltage_step_uV:
                self.voltage_set_uV = self._cfg.voltage_step_uV
                self.is_rising = True
                self.volt_step_uV = self._cfg.voltage_step_uV

        return _voltage_uV, _current_nA

    def ivcurve_2_mppt_opt(self, _voltage_uV: int, _current_nA: int) -> Tuple[int, int]:
        self.age_now += 1
        self.age_nxt += 1

        power_fW = _voltage_uV * _current_nA
        if (
            (power_fW > self.power_nxt)
            and (_voltage_uV >= self._cfg.voltage_min_uV)
            and (_voltage_uV <= self._cfg.voltage_max_uV)
        ):
            self.age_nxt = 0
            self.power_nxt = power_fW
            self.voltage_nxt = _voltage_uV
            self.current_nxt = _current_nA

        if (self.age_now > self._cfg.window_size) or (self.power_nxt >= self.power_now):
            self.age_now = self.age_nxt
            self.power_now = self.power_nxt
            self.voltage_now = self.voltage_nxt
            self.current_now = self.current_nxt
            self.age_nxt = 0
            self.power_nxt = 0
            self.voltage_nxt = 0
            self.current_nxt = 0

        return self.voltage_now, self.current_now
