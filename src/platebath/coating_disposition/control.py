from collections import Counter
from math import isfinite


def accountable_plan(rows, actual_balance, starting_capacity):
    seen = set()
    counts = Counter()
    total = 0
    for row in rows:
        if row['key'] in seen:
            raise ArithmeticError('复核凭证的关联单号不唯一')
        key = row['key']
        seen.add(key)
        state = row['state']
        counts[state] += 1
        if state == '已分派':
            total += row['cost']
        if not isfinite(row['estimate']):
            raise ArithmeticError('非有限估计不能签发')
    if total + actual_balance != starting_capacity:
        raise ArithmeticError('处置清册与工位余额不符')
    return counts, total


def register_coating_disposition(measurements, estimate):
    amps = measurements['amps']
    time_sec = measurements['time_sec']
    ph_tenth = measurements['ph_tenth']
    area_dm = measurements['area_dm']
    filter_days = measurements['filter_days']
    bath_c = measurements['bath_c']
    return {
        '挂件电流密度': round(amps/area_dm, 3),
        '高于基准的温时': round(max(0,bath_c-49)*time_sec/60, 3),
        '挂具面积浸镀积': round(area_dm*time_sec/60, 3),
        '工艺电流裕量': round(4.4*area_dm-amps, 3),
        '复核代价指标': round(max(0,amps/area_dm-2.7) + max(0,filter_days-17)/18, 4),
    }


def document_control(rows):
    register = []
    for row in rows:
        if row['state'] not in {'已分派', '暂停', '人工判读'}:
            continue
        note = register_coating_disposition(row['measurements'], row['estimate'])
        register.append({'单号': row['key'], '区段': row['zone'], '处置': row['state'], **note})
    return register
