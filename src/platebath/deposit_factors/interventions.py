from dataclasses import replace
from statistics import median

from .contracts import DepositFactors, Proposal


def measure_deposit_factors(values) -> DepositFactors:
    amps, time_sec, ph_tenth, area_dm, filter_days, bath_c = values
    return DepositFactors(
        current_flux=amps/area_dm,
        coulomb_area=amps*time_sec/area_dm,
        warm_minutes=max(0,bath_c-49)*time_sec/60,
        ph_alkali=max(0,ph_tenth-49)/10,
        ph_acid=max(0,49-ph_tenth)/10,
        bath_service=32-filter_days,
        area_minutes=area_dm*time_sec/60,
        current_headroom=4.4*area_dm-amps,
    )


def propose_retest_bench(values, missing=()):
    amps, time_sec, ph_tenth, area_dm, filter_days, bath_c = values
    if 'amps' not in missing and (amps>=84):
        yield Proposal('调整下一挂电流', 'amps', amps, max(60,amps-24), 1)
    if 'time_sec' not in missing and (time_sec>=128):
        yield Proposal('小挂具缩短浸镀', 'time_sec', time_sec, max(80,time_sec-48), 1)
    if 'ph_tenth' not in missing and (abs(ph_tenth-49)>=5):
        yield Proposal('槽液回调一个档', 'ph_tenth', ph_tenth, 49, 2)
    if 'filter_days' not in missing and (filter_days>=14):
        yield Proposal('换滤芯后再测', 'filter_days', filter_days, 0, 3)
