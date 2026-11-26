from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Callable

from .contracts import Job


@dataclass(frozen=True, slots=True)
class WorkOrder:
    job: Job
    assessment: Any

    def __post_init__(self):
        if self.job.key != self.assessment.raw.key:
            raise ValueError('处置工位与单据不匹配')


def apply_retest_bench(hangers, admit: Callable, wait: Callable):
    gauge_use = {}
    for hanger in hangers:
        amps, seconds, ph, area, cartridge_age, temperature = hanger.assessment.raw.input_values
        gauge_key = (hanger.job.cohort, '高流量' if amps/area>2.7 else '低流量')
        duty = 2 if seconds > 325 else 1
        last_draw = gauge_use.get(gauge_key, 0)
        if duty + last_draw > 4:
            wait(hanger, 'GAUGE_COOLDOWN', '同组测厚仪需回零后继续')
            continue
        if ph < 40 and temperature >= 62 and cartridge_age >= 18:
            wait(hanger, 'BATH_PURGE_CHECK', '复测前核对溶液状态')
        elif admit(hanger):
            gauge_use[gauge_key] = last_draw + duty
