from .operating_ledger import operating_ledger
from collections import Counter, defaultdict
from math import exp, fsum, isfinite

from .contracts import RuleNotice, Job, Plan, Policy, RISK_CUTOFF
from .constraints import WorkOrder, apply_retest_bench, GAUGE_DUTY_LIMIT
from .optimizer import optimal_selection, expected_hits, descriptor as gauge_descriptor
from ..gauge_bands.service import (
    calibrate_overrun_risk,
    calibrate_risk,
    risk_probability,
    overrun_probability,
)


def measures(raw):
    return tuple(raw)


def signals(data, estimate, missing=()):
    absent=frozenset(missing)
    amps, time_sec, ph_tenth, area_dm, filter_days, bath_c = data
    hits = []
    if not absent.intersection(('amps', 'area_dm')) and (amps/area_dm > 4.4):
        hits.append(RuleNotice('DENSITY_LIMIT', '挂件单位电流超工艺上限', hard=True))
    if not absent.intersection(('ph_tenth', 'filter_days')) and (filter_days >= 24 and ph_tenth >= 55):
        hits.append(RuleNotice('AGED_FILTER', '槽液老化，追加厚度复测', hard=False))
    if not absent.intersection(('time_sec', 'area_dm')) and (area_dm < 60 and time_sec > 390):
        hits.append(RuleNotice('LOW_LOAD', '小挂具长浸镀', hard=False))
    return tuple(hits)


def expected_load(measurements):
    amps, time_sec, ph_tenth, area_dm, filter_days, bath_c = measurements
    return 1 + int(area_dm >= 100)


def dispatch_pressure(values, estimate):
    amps, time_sec, ph_tenth, area_dm, filter_days, bath_c = values
    return max(0,amps/area_dm-2.7) + max(0,filter_days-17)/18


def confidence_weight(estimate, cutoff):
    shifted = (estimate - cutoff) / max(.5, abs(cutoff) * .35)
    if shifted >= 0:
        return 1 / (1 + exp(-shifted))
    bounded = exp(shifted)
    return bounded / (1 + bounded)


def risk_is_ready(risk):
    if risk is None:
        return False
    ready = getattr(risk, 'ready', None)
    if ready is not None:
        return bool(ready)
    requires_review = getattr(risk, 'requires_review', None)
    if requires_review is not None:
        return not bool(requires_review)
    positives = getattr(risk, 'positives', None)
    size = getattr(risk, 'size', None)
    if positives is not None and size is not None:
        return 0 < positives < size
    return True


def calibrated_probability(risk, assessment):
    if risk is None:
        return None
    if isinstance(risk, dict):
        if assessment.raw.key in risk:
            value = risk[assessment.raw.key]
        elif 'probability' in risk:
            value = risk['probability']
        else:
            return None
    elif callable(risk) and not hasattr(risk, 'probability_for'):
        try:
            value = risk(assessment)
        except TypeError:
            value = risk(assessment.raw.key)
    else:
        method = getattr(risk, 'probability_for', None)
        if method is None:
            method = getattr(risk, 'probability', None)
        if method is None:
            return None
        try:
            value = method(assessment)
        except TypeError:
            value = method(estimate=assessment.estimate)
    if value is None:
        return None
    value = float(value)
    if not isfinite(value):
        raise ValueError('超线概率必须为有限值')
    return min(1.0, max(0.0, value))


def recommend(assessment, attention, policy, risk=None):
    raw = assessment.raw
    data = measures(raw.input_values)
    estimate = assessment.estimate
    domain_codes = signals(data, estimate, raw.missing)
    legacy_level = confidence_weight(estimate, policy.trigger)
    cost = expected_load(data)
    if not isfinite(estimate) or not 1 <= cost <= 12:
        raise ValueError('处置量不在有效范围')

    if risk is not None and risk_is_ready(risk):
        probability = calibrated_probability(risk, assessment)
    elif risk is None:
        injected = getattr(assessment, 'probability', None)
        probability = None if injected is None else min(1.0, max(0.0, float(injected)))
    else:
        probability = None
    level = probability if probability is not None else legacy_level
    # Internal/legacy callers do not supply an independent risk calibration.
    # Keep the stable logistic priority available as their probability value;
    # an explicitly invalid calibration instead leaves probability undefined.
    if probability is not None:
        job_probability = probability
    elif risk is None:
        job_probability = legacy_level
    else:
        job_probability = None
    if domain_codes and domain_codes[0].hard:
        state = '暂停'
        reason = domain_codes[0].rule_id
        summary = domain_codes[0].meaning
    elif raw.key in attention or assessment.uncertain:
        state = '人工判读'
        reason = 'OUT_OF_REFERENCE' if raw.key in attention else 'INSUFFICIENT_CALIBRATION'
        summary = '分布偏移或校准量不足，需核对原始单据'
    elif risk is not None and not risk_is_ready(risk):
        state = '人工判读'
        reason = 'INSUFFICIENT_CALIBRATION'
        summary = '独立校准窗缺少超线或未超线实绩，需人工判读'
    else:
        rule_candidate = bool(domain_codes)
        model_candidate = estimate >= policy.trigger
        risk_candidate = probability is not None and probability > 0
        if rule_candidate or model_candidate or risk_candidate:
            state = '候选'
            if domain_codes:
                reason = domain_codes[0].rule_id
                summary = domain_codes[0].meaning
            elif model_candidate:
                reason = 'ABOVE_TRIGGER'
                summary = '达到本班复核阈值'
            else:
                reason = 'CALIBRATED_OVERRUN_RISK'
                summary = '独立校准实绩显示未到厚差线仍可能超线'
        else:
            state = '观察'
            reason = 'BELOW_TRIGGER'
            summary = '保留记录并等待下一次巡查'
    return Job(raw.key, raw.cohort, round(estimate, 4), assessment.lower, assessment.upper, cost,
               state, reason, summary, round(level, 5), tuple(item.rule_id for item in domain_codes),
               job_probability)


def allocate(assessments, attention, policy, risk=None):
    work = [WorkOrder(recommend(assessment, attention, policy, risk), assessment) for assessment in assessments]
    if len({item.job.key for item in work}) != len(work):
        raise ValueError('待处理单据编号重复')
    candidates = sorted((order for order in work if order.job.state == '候选'),
                        key=lambda order: (not bool(order.job.rule_hits), -dispatch_pressure(order.assessment.raw.input_values, order.job.estimate),
                                           -order.job.priority, order.job.cost, order.job.key))
    selected_keys = optimal_selection(
        candidates,
        capacity=policy.capacity,
        group_quota=policy.group_quota,
        already_ranked=True,
    )
    selected_orders = [order for order in candidates if order.job.key in selected_keys]
    final_group_used = Counter(order.job.cohort for order in selected_orders for _ in range(order.job.cost))
    final_slot_used = sum(order.job.cost for order in selected_orders)
    final_gauge_used = Counter()
    for order in selected_orders:
        desc = gauge_descriptor(order)
        if desc is not None:
            duty, flow, _ = desc
            final_gauge_used[(order.job.cohort, flow)] += duty
    remaining = policy.capacity
    used = defaultdict(int)
    allocated = {}

    def wait(order, reason, evidence):
        allocated[order.job.key] = order.job.change('候补', reason, evidence)

    def admit(order):
        nonlocal remaining
        job = order.job
        if job.key not in selected_keys:
            # Classify against the complete signed set, including resources
            # reserved by lower-ranked selected hangers processed later.
            if final_slot_used + job.cost > policy.capacity:
                wait(order,'CAPACITY_REACHED','剩余作业额度不足')
                return False
            if final_group_used.get(job.cohort, 0) + job.cost > policy.group_quota:
                wait(order,'GROUP_CAP_REACHED','已达分区额度上限')
                return False
            desc = gauge_descriptor(order)
            if desc is not None:
                duty, flow, _ = desc
                if final_gauge_used.get((job.cohort, flow), 0) + duty > GAUGE_DUTY_LIMIT:
                    wait(order,'GAUGE_COOLDOWN','同组测厚仪需回零后继续')
                    return False
            wait(order,'RISK_RETURN_NOT_OPTIMAL','该组合的预计超线挂具数不是最多')
            return False
        if job.cost > remaining:
            wait(order,'CAPACITY_REACHED','剩余作业额度不足')
            return False
        if used.get(job.cohort, 0) + job.cost > policy.group_quota:
            wait(order,'GROUP_CAP_REACHED','已达分区额度上限')
            return False
        remaining -= job.cost
        used[job.cohort] += job.cost
        allocated[job.key] = job.change('已分派', job.reason, job.summary)
        return True

    apply_retest_bench(candidates, admit, wait)
    if set(allocated) != {item.job.key for item in candidates}:
        raise ArithmeticError('存在未经过工位规则的候选单据')
    dispatched_keys = {key for key, job in allocated.items() if job.state == '已分派'}
    if dispatched_keys != set(selected_keys):
        # The optimizer models the same capacity, cohort and gauge resources as
        # apply_retest_bench; a mismatch means one of those calculations drifted.
        raise ArithmeticError('最优名单与工位占用不一致')
    resolved = sorted((allocated.get(item.job.key,item.job) for item in work),
                      key=lambda job: (job.state != '已分派', job.state == '观察',
                                       -(job.probability if job.probability is not None else job.priority),
                                       -job.priority, job.key))
    if sum(used.values()) + remaining != policy.capacity:
        raise ArithmeticError('派发余额核对失败')
    expected_hits = fsum((job.probability if job.probability is not None else 0.0)
                         for job in allocated.values() if job.state == '已分派')
    risk_ready = risk_is_ready(risk) if risk is not None else True
    return Plan(tuple(resolved), policy.capacity, remaining, tuple(sorted(used.items())),
                round(expected_hits, 6), risk_ready)


def plan_jobs(assessments, attention=(), capacity=12, mode='balanced', calibration=None, *extra, **options):
    risk = calibration
    for name in ('risk', 'risk_calibration', 'risk_profile', 'risk_model',
                 'probabilities', 'risk_probabilities', 'probability_by_key',
                 'probability_map', 'risk_probability'):
        if risk is None and options.get(name) is not None:
            risk = options[name]
    policy = options.get('policy')

    # Tolerate call shapes such as plan_jobs(rows, attention, Policy, risk)
    # and plan_jobs(rows, Policy, risk).
    if policy is None and isinstance(attention, Policy):
        policy = attention
        attention = ()
        if risk is None and capacity is not None and not isinstance(capacity, int):
            risk = capacity
    if policy is None and isinstance(capacity, Policy):
        policy = capacity
        if risk is None and mode is not None and not isinstance(mode, str):
            risk = mode
    if policy is None and isinstance(mode, Policy):
        policy = mode
    if extra and risk is None:
        risk = extra[0]
    if isinstance(risk, (list, tuple)) and not hasattr(risk, 'probability_for'):
        # Raw mature calibration rows can be supplied without first calling
        # the gauge calibration factory.
        from ..gauge_bands.service import calibrate_overrun_risk
        risk = calibrate_overrun_risk(risk)
    if policy is None:
        policy = Policy.select(capacity, mode if isinstance(mode, str) else 'balanced')
    return allocate(assessments, frozenset(() if attention is None else attention), policy, risk)


def optimize_dispatch(jobs, capacity=12, mode='focus', **kwargs):
    policy = kwargs.pop('policy', None) or Policy.select(capacity, mode)
    return optimal_selection(jobs, capacity=policy.capacity, group_quota=policy.group_quota, **kwargs)


def expected_overrun_hits(plan_or_jobs):
    jobs = getattr(plan_or_jobs, 'jobs', plan_or_jobs)
    return expected_hits(job for job in jobs if getattr(job, 'state', '已分派') == '已分派')


def action_evidence(plan):
    counts = Counter(job.state for job in plan.jobs)
    status = [{'处置': state, '单量': count} for state, count in sorted(counts.items())]
    status.extend({'处置': '分区 ' + group, '额度': cost} for group, cost in plan.used_by_group)
    status += [{'处置': '剩余额度', '额度': plan.balance}]
    return status


def work_basin(raw):
    area_dm = raw[3]
    return int(area_dm//35)


def operating_group(assessments, progression):
    source={line.raw.key:line.raw.input_values for line in assessments}
    cells=Counter()
    for work in progression.jobs:
        if work.state != '已分派':
            continue
        band=work_basin(source[work.key])
        cells[work.cohort,band] += work.cost
    return [{ '作业区': zone, '挂具档': band, '班组用量': total } for (zone,band),total in sorted(cells.items())]
