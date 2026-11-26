from dataclasses import dataclass
from math import sqrt, fsum
from statistics import median


@dataclass(frozen=True, slots=True)
class DomainStudy:
    counts: tuple[int, int, int]
    rate: float | None
    midpoint: float | None
    expected: float | None
    drift: float | None

def solution_mix_domains(vectors):
    current_flux = []
    coulomb_area = []
    warm_minutes = []
    ph_alkali = []
    ph_acid = []
    bath_service = []
    area_minutes = []
    current_headroom = []
    for measurement in vectors:
        unobserved = frozenset(measurement.missing)
        amps, time_sec, ph_tenth, area_dm, filter_days, bath_c = measurement.input_values
        if unobserved.isdisjoint(('amps', 'area_dm')):
            current_flux.append((round(amps/area_dm, 4), amps/area_dm>2.7))
        if unobserved.isdisjoint(('amps', 'time_sec', 'area_dm', 'filter_days')):
            coulomb_area.append((round(amps*time_sec/area_dm, 4), filter_days>=20))
        if unobserved.isdisjoint(('time_sec', 'ph_tenth', 'bath_c')):
            warm_minutes.append((round(max(0,bath_c-49)*time_sec/60, 4), ph_tenth>=56))
        if unobserved.isdisjoint(('time_sec', 'ph_tenth')):
            ph_alkali.append((round(max(0,ph_tenth-49)/10, 4), time_sec>=320))
        if unobserved.isdisjoint(('ph_tenth', 'area_dm', 'bath_c')):
            ph_acid.append((round(max(0,49-ph_tenth)/10, 4), bath_c>=55 and area_dm<90))
        if unobserved.isdisjoint(('amps', 'area_dm', 'filter_days')):
            bath_service.append((round(32-filter_days, 4), amps/area_dm>2.7))
        if unobserved.isdisjoint(('time_sec', 'area_dm', 'filter_days')):
            area_minutes.append((round(area_dm*time_sec/60, 4), filter_days>=20))
        if unobserved.isdisjoint(('amps', 'ph_tenth', 'area_dm')):
            current_headroom.append((round(4.4*area_dm-amps, 4), ph_tenth>=56))
    return {
        '挂件电流密度 · 密挂电流高': tuple(current_flux),
        '每平方分米库仑 · 老滤芯': tuple(coulomb_area),
        '高于基准的温时 · 酸碱偏高': tuple(warm_minutes),
        '高酸碱度方向 · 长时间镀覆': tuple(ph_alkali),
        '低酸碱度方向 · 补镀线热槽': tuple(ph_acid),
        '滤芯剩余巡查天数 · 密挂电流高': tuple(bath_service),
        '挂具面积浸镀积 · 老滤芯': tuple(area_minutes),
        '工艺电流裕量 · 酸碱偏高': tuple(current_headroom),
    }


def evaluate_domains(training, current):
    references = solution_mix_domains(training)
    activity = solution_mix_domains(current)
    diagnostics = []
    for domain, observed in activity.items():
        baseline = references.get(domain, ())
        study = characterize(baseline, observed)
        diagnostics.append({'观察维度': domain, '训练有效量': study.counts[0], '当班有效量': study.counts[1],
                            '越线量':study.counts[2], '越线比例':study.rate, '参考中位':study.midpoint,
                            '当班中位':study.expected, '相对训练变化':study.drift})
    return diagnostics


def characterize(before, after):
    history = tuple(value for value, _ in before)
    observed = tuple(value for value, _ in after)
    violating = sum(flag for _, flag in after)
    old = median(history) if history else None
    new = median(observed) if observed else None
    pct = round(violating / len(after), 4) if after else None
    movement = round(new - old, 4) if old is not None and new is not None else None
    return DomainStudy((len(before),len(after),violating),pct,old,new,movement)
