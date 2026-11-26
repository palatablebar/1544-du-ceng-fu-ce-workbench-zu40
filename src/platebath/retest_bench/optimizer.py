"""Exact small-slot selection for retest work.

The bench has at most 60 slot units.  Hangers normally cost one or two slots,
while each cohort has a quota and each cohort/flow meter has a cooldown duty
budget.  This module optimizes summed probabilities (expected over-line
hanger count) instead of greedily taking the individually riskiest hanger.
"""

from collections import defaultdict
from math import fsum, isfinite

from .constraints import GAUGE_DUTY_LIMIT


def as_job(item):
    job = getattr(item, 'job', None)
    if job is not None:
        return job
    if isinstance(item, tuple) and item and hasattr(item[0], 'key'):
        return item[0]
    return item


def probability_of(item):
    job = as_job(item)
    value = getattr(job, 'probability', None)
    if value is None:
        value = getattr(job, 'priority', 0.0)
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not isfinite(value):
        return 0.0
    return min(1.0, max(0.0, value))


def descriptor(item):
    """Return gauge resource use, or None when raw measurements are absent."""
    assessment = getattr(item, 'assessment', None)
    if assessment is None and isinstance(item, tuple) and len(item) > 1:
        assessment = item[1]
    raw = getattr(assessment, 'raw', None)
    values = getattr(raw, 'input_values', None)
    if values is None:
        return None
    try:
        amps, seconds, ph, area, cartridge_age, temperature = values
        if not all(isfinite(float(value)) for value in values):
            return None
        if area <= 0:
            return None
    except (TypeError, ValueError, ZeroDivisionError):
        return None

    flow = 0 if amps / area > 2.7 else 1
    duty = 2 if seconds > 325 else 1
    purge_blocked = ph < 40 and temperature >= 62 and cartridge_age >= 18
    return duty, flow, purge_blocked


def default_rank(item):
    job = as_job(item)
    probability = probability_of(item)
    return (-probability, int(job.cost), str(job.key))


def _better(candidate, current):
    if current is None:
        return True
    candidate_score, candidate_mask = candidate
    current_score, current_mask = current
    # Clear shop-floor differences are never lost to summation noise; tiny
    # floating artifacts defer to the deterministic priority mask.
    return (round(candidate_score, 12), candidate_mask) > (round(current_score, 12), current_mask)


def _group_menu(items, item_mask, quota, gauge_limit):
    # Resource tuple is (slot cost, high-flow duty, low-flow duty).  When raw
    # gauge data is unavailable for plain Job tests, only slot cost is used.
    constrained = all(descriptor(item) is not None for item in items)
    zero_resource = (0, 0, 0) if constrained else (0,)
    states = {zero_resource: (0.0, 0)}

    for item in items:
        job = as_job(item)
        cost = int(job.cost)
        if cost <= 0 or cost > quota:
            continue
        desc = descriptor(item)
        if desc is not None and desc[2]:
            continue
        duty, flow, _ = desc if constrained and desc is not None else (0, None, False)

        for resource, current in tuple(states.items()):
            used_cost = resource[0]
            new_cost = used_cost + cost
            if new_cost > quota:
                continue
            if constrained:
                high_used, low_used = resource[1], resource[2]
                gauge_used = high_used if flow == 0 else low_used
                if gauge_used + duty > gauge_limit:
                    continue
                new_resource = (
                    new_cost,
                    high_used + (duty if flow == 0 else 0),
                    low_used + (duty if flow == 1 else 0),
                )
            else:
                new_resource = (new_cost,)

            score, mask = current
            candidate = (score + probability_of(item), mask | item_mask[job.key])
            if _better(candidate, states.get(new_resource)):
                states[new_resource] = candidate

    menu = {}
    for resource, value in states.items():
        cost = resource[0]
        if cost > quota:
            continue
        if _better(value, menu.get(cost)):
            menu[cost] = value
    return menu


def optimal_selection(items, *, capacity, group_quota=None, gauge_limit=GAUGE_DUTY_LIMIT,
                      already_ranked=False):
    """Return the deterministic set of keys maximizing summed probability."""
    orders = list(items)
    if not already_ranked:
        orders.sort(key=default_rank)
    if type(capacity) is not int or not 0 <= capacity <= 60:
        # Policy validation normally runs first; keep this helper defensive.
        capacity = max(0, min(60, int(capacity)))
    quota = capacity if group_quota is None else min(int(group_quota), capacity)

    # High bits correspond to early ranks.  Maximizing the integer therefore
    # reproduces the bench's stable priority order for exact objective ties.
    count = len(orders)
    masks = {as_job(item).key: 1 << max(0, count - 1 - index)
             for index, item in enumerate(orders)}

    by_cohort = defaultdict(list)
    for item in orders:
        job = as_job(item)
        by_cohort[str(job.cohort)].append(item)

    dp = {0: (0.0, 0)}
    for cohort in sorted(by_cohort):
        menu = _group_menu(by_cohort[cohort], masks, quota, gauge_limit)
        options = [(0, 0.0, 0)]
        options.extend((cost, score, mask) for cost, (score, mask) in sorted(menu.items()) if cost)
        next_dp = {}
        for used, (score, mask) in dp.items():
            for cost, group_score, group_mask in options:
                total_cost = used + cost
                if total_cost > capacity:
                    continue
                candidate = (score + group_score, mask | group_mask)
                if _better(candidate, next_dp.get(total_cost)):
                    next_dp[total_cost] = candidate
        dp = next_dp

    if not dp:
        return frozenset()
    best_used, (best_score, best_mask) = max(
        dp.items(), key=lambda entry: (round(entry[1][0], 12), entry[1][1], -entry[0])
    )
    return frozenset(key for key, mask in masks.items() if mask & best_mask)


# Readable aliases for callers/tests describing the same operation.
optimal_keys = optimal_selection
max_expected_hits = optimal_selection
optimize_retests = optimal_selection
optimal_plan = optimal_selection
optimal_dispatch = optimal_selection
select_optimal = optimal_selection
select_retests = optimal_selection
choose_retests = optimal_selection
optimize_plan = optimal_selection
dispatch_selection = optimal_selection


def expected_hits(items):
    return round(fsum(probability_of(item) for item in items), 6)
