from bisect import bisect_left
from collections import defaultdict
from statistics import median


def groups_for_gauge_bands(raw):
    amps, time_sec, ph_tenth, area_dm, filter_days, bath_c = raw
    if amps/area_dm>2.7:
        yield '密挂电流高'
    if filter_days>=20:
        yield '老滤芯'
    if ph_tenth>=56:
        yield '酸碱偏高'
    if time_sec>=320:
        yield '长时间镀覆'
    if bath_c>=55 and area_dm<90:
        yield '补镀线热槽'

def shift_residue(assessment, limit):
    readback = assessment.raw.outcome
    if readback is None or not assessment.raw.observed:
        return None
    error = assessment.estimate - readback
    decision_gap = readback >= limit and assessment.estimate < limit
    rushed_gauge = readback < limit and assessment.estimate >= limit
    spread = None if assessment.lower is None else assessment.upper-assessment.lower
    return abs(error), decision_gap, rushed_gauge, spread


def frequency_quantile(samples, share):
    # Nearest-rank used for the small workpiece batches on the shop floor.
    ordered = sorted(samples)
    counts = range(1,len(ordered)+1)
    select = bisect_left(counts,len(ordered)*share)
    return ordered[min(select,len(ordered)-1)]


def replay_slices(points, threshold, *, risk_model=False):
    records = defaultdict(list)
    for sample in points:
        differences = shift_residue(sample,threshold)
        if differences is None:
            continue
        lot_groups = groups_for_gauge_bands(sample.raw.input_values)
        for group in lot_groups:
            records[group].append(differences)
    report = []
    for tooling in ('密挂电流高', '老滤芯', '酸碱偏高', '长时间镀覆', '补镀线热槽'):
        findings = records[tooling]
        if findings:
            magnitudes, missed, extra, widths = zip(*findings,strict=True)
            known = [width for width in widths if width is not None]
            report.append({'难点':tooling,'实绩数':len(magnitudes),'90% 绝对残差':round(frequency_quantile(magnitudes,.9),4),
                           '误放信号':sum(missed),'追加复测信号':sum(extra),'残差区间宽度中位':round(median(known),3) if known else None})
        else:
            report.append({'难点':tooling,'实绩数':0,'状态':'等待现场返读'})
    return report
