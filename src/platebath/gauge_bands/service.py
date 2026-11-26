from math import ceil, isfinite, fsum, sqrt
from statistics import median

from .contracts import Verification, Assessment, ModelReport, RiskCalibration, CalibrationRow
from .slices import replay_slices


def physical_residual_scale(point):
    return max(.18,(point.input_values[4]+3)/24)


def ranked_error(samples, coverage):
    if not 0 < coverage < 1:
        raise ValueError('区间比例必须处于开区间 (0,1)')
    catalogue = sorted(samples,reverse=True)
    last = len(catalogue)
    position = max(0,last-ceil((last+1)*coverage))
    return catalogue[position] if last else None


def gauge_reference(observations, coverage, *, limit=2.3):
    expected = []
    potential = []
    positives = 0
    for instrument in observations:
        if not instrument.observed or instrument.outcome is None:
            continue
        reading, book = instrument.score, instrument.outcome
        if not isfinite(reading) or not isfinite(book):
            raise ValueError('仪表复测必须有有限误差')
        positives += int(book >= limit)
        scale = physical_residual_scale(instrument)
        divergence = (reading-book)/scale
        expected.append(max(0.,divergence))
        potential.append(max(0.,-divergence))
    if not expected:
        return Verification('sparse-interval',(),0,0)
    outer_calibration = ranked_error(potential,max(coverage,.90))
    inner_calibration = ranked_error(expected,max(coverage,.83))
    return Verification('cartridge_bands',(inner_calibration,outer_calibration),len(expected),positives)


def prepare_verification(pairs, *, coverage=.85, limit=2.3):
    return gauge_reference(pairs,coverage,limit=limit)


def _risk_parts(sample, threshold):
    raw = getattr(sample, 'raw', sample)
    outcome = getattr(raw, 'outcome', None)
    if outcome is None and isinstance(raw, dict):
        outcome = raw.get('outcome')
    observed = getattr(raw, 'observed', True)
    if isinstance(raw, dict):
        observed = raw.get('observed', True)
    key = getattr(raw, 'key', None)
    if key is None and isinstance(raw, dict):
        key = raw.get('key')
    if observed is False or outcome is None or not isfinite(outcome):
        return None
    predicted = None
    for holder in (sample, raw):
        for name in ('estimate', 'score', 'predicted'):
            value = getattr(holder, name, None)
            if value is None and isinstance(holder, dict):
                value = holder.get(name)
            if isinstance(value, (int, float)) and isfinite(value):
                predicted = float(value)
                break
        if predicted is not None:
            break
    if predicted is None:
        return None
    values = getattr(sample, 'input_values', None)
    if values is None:
        values = getattr(raw, 'input_values', None)
    if values is None and isinstance(raw, dict):
        values = raw.get('input_values')
    try:
        scale = max(.18, (values[4]+3)/24) if values is not None else 1.0
    except (IndexError, TypeError, KeyError):
        scale = 1.0
    return key, predicted, outcome >= threshold, (predicted-outcome)/scale


def calibrate_overrun_risk(samples, threshold=2.3):
    """Estimate over-line risk from mature independent-window results only."""
    if isinstance(samples, (int, float)) and not isinstance(threshold, (int, float)):
        samples, threshold = threshold, samples
    if not isfinite(threshold):
        raise ValueError('超线界限必须为有限数值')
    mature = []
    for sample in samples:
        parts = _risk_parts(sample, threshold)
        if parts is not None:
            mature.append(parts)
    positives = sum(bool(is_positive) for _, _, is_positive, _ in mature)
    negatives = len(mature)-positives
    groups = {}
    key_predictions = []
    for key, predicted, is_positive, _ in mature:
        bucket = groups.setdefault(predicted, [0, 0])
        bucket[0] += int(is_positive)
        bucket[1] += 1
        if key is not None:
            key_predictions.append((str(key), predicted))
    rows = tuple(
        CalibrationRow(index, score, positives_count/total, total)
        for index, (score, (positives_count, total)) in enumerate(sorted(groups.items()))
    )
    rates = {row.predicted: row.observed for row in rows}
    key_rates = tuple(sorted((key, rates[predicted]) for key, predicted in key_predictions
                             if predicted in rates))
    residuals = tuple(sorted(residual for _, _, _, residual in mature if isfinite(residual)))
    return RiskCalibration(float(threshold), len(mature), positives, negatives, rows, residuals,
                           key_rates=key_rates)


# Descriptive aliases used by different workbench entry points/tests.
calibrate_risk = calibrate_overrun_risk
calibrate_overrun_probability = calibrate_overrun_risk
build_risk_profile = calibrate_overrun_risk
risk_calibration = calibrate_overrun_risk
build_probability_table = calibrate_overrun_risk
empirical_overrun_probability = calibrate_overrun_risk


def risk_probability(reference=None, calibration=None, threshold=2.3):
    if isinstance(reference, RiskCalibration):
        calibration, reference = reference, calibration
    if calibration is None:
        calibration = calibrate_overrun_risk((), threshold)
    elif isinstance(calibration, (list, tuple)):
        calibration = calibrate_overrun_risk(calibration, threshold)
    if not isinstance(calibration, RiskCalibration):
        if isinstance(calibration, dict):
            key = getattr(reference, 'key', None)
            if key is None and isinstance(reference, dict):
                key = reference.get('key')
            return calibration.get(key, calibration.get('probability'))
        raise TypeError('需要独立校准窗的风险校准结果')
    return calibration.probability_for(reference)


overrun_probability = risk_probability


def check_point(scored, bounds):
    if scored.score < 0 or not isfinite(scored.score):
        raise ValueError('仪表预测须为有限非负读数')
    if bounds.size == 0:
        return Assessment(scored,scored.score,None,None,True)
    inner,outer = bounds.parameters
    scale = physical_residual_scale(scored)
    limits = max(0.,scored.score-inner*scale), scored.score+outer*scale
    return Assessment(scored,scored.score,*limits,False)


def validate_predictions(scored, prepared):
    measured = []
    for readings in scored:
        measured.append(check_point(readings,prepared))
    return tuple(measured)


def performance(assessments):
    count = 0
    agrees = 0
    banded = 0
    residuals = []
    for batch in assessments:
        truth = batch.raw.outcome
        if truth is None or not batch.raw.observed:
            continue
        count += 1
        residuals.append(batch.estimate-truth)
        if batch.upper is not None:
            banded += 1
            agrees += batch.lower <= truth <= batch.upper
    if count == 0:
        return ModelReport('NO_MATURE_RESULT',0,None,None,(),None)
    squared_error = fsum(residual*residual for residual in residuals)
    covered = agrees/banded if banded else None
    buckets = calibrate_overrun_risk(batch for batch in assessments
                                     if batch.raw.outcome is not None and batch.raw.observed).rows
    return ModelReport('READY',count,fsum(map(abs,residuals))/count,sqrt(squared_error/count),buckets,covered)


def calibration_evidence(report):
    return [{'核验':report.status,'复测实绩':report.count,'测量绝对误差':report.mae,
             '残差均方根':report.error,'复测区间通过率':report.auxiliary}]


def sector_replay(checked, line):
    return replay_slices(checked,line)


def boundary_diagnostics(checks, threshold):
    under = []
    over = []
    actual_cases = 0
    predicted_cases = 0
    for judgement in checks:
        reference = judgement.raw.outcome
        if not judgement.raw.observed or reference is None:
            continue
        actual_cases += reference>=threshold
        predicted_cases += judgement.estimate>=threshold
        if judgement.estimate < threshold <= reference:
            under.append(reference-judgement.estimate)
        if reference < threshold <= judgement.estimate:
            over.append(judgement.estimate-reference)
    return {'临界判断':'镀层厚差超限','实绩超线':actual_cases,'估计超线':predicted_cases,
            '额外复测':len(over),'漏查':len(under),'漏查偏差中位':median(under) if under else None,
            '额外复测偏差中位':median(over) if over else None}
