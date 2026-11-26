from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JointAction:
    case: str
    work_units: int
    notes: str
    changes: dict[str, tuple[float, float]]

    def evidence(self, old_value, new_value, extrapolates):
        return {'联动推演':self.case, '用量':self.work_units, '先决条件':self.notes,
                '原预测':round(old_value,4), '替换预测':round(new_value,4),
                '变化':round(new_value-old_value,4), '超训练域':bool(extrapolates),
                '联动量测':{item:{'原值':before,'替换值':after} for item,(before,after) in self.changes.items()}}


def simulate_retune_bath(readings, invalid):
    amps, time_sec = readings[0], readings[1]
    if invalid.intersection(('amps', 'time_sec')):
        return None
    if not (amps>=86 and time_sec>=130):
        return None
    amps_adjusted = amps-24
    time_sec_adjusted = time_sec-40
    inspected = {
        'amps': (amps, amps_adjusted),
        'time_sec': (time_sec, time_sec_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('换小电流档并减时', 2, '下一挂进行工艺对照', inspected)
    return None


def simulate_refresh_bath_solution(readings, invalid):
    ph_tenth, filter_days = readings[2], readings[4]
    if invalid.intersection(('ph_tenth', 'filter_days')):
        return None
    if not (abs(ph_tenth-49)>=6 and filter_days>=10):
        return None
    ph_tenth_adjusted = 49
    filter_days_adjusted = 0
    inspected = {
        'ph_tenth': (ph_tenth, ph_tenth_adjusted),
        'filter_days': (filter_days, filter_days_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('重调酸碱换滤芯', 3, '复测前确认新滤芯以来的槽液状态', inspected)
    return None


def simulate_cool_soak(readings, invalid):
    time_sec, bath_c = readings[1], readings[5]
    if invalid.intersection(('time_sec', 'bath_c')):
        return None
    if not (bath_c>=45 and time_sec<=380):
        return None
    bath_c_adjusted = bath_c-7
    time_sec_adjusted = time_sec+50
    inspected = {
        'bath_c': (bath_c, bath_c_adjusted),
        'time_sec': (time_sec, time_sec_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('降温试镀延长', 2, '降低液温后采用低节拍试挂', inspected)
    return None


def simulate_reduce_hanger_batch(readings, invalid):
    amps, area_dm = readings[0], readings[3]
    if invalid.intersection(('amps', 'area_dm')):
        return None
    if not (area_dm>=60 and amps>=98):
        return None
    area_dm_adjusted = area_dm-27
    amps_adjusted = amps-32
    inspected = {
        'area_dm': (area_dm, area_dm_adjusted),
        'amps': (amps, amps_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('拆挂具并按面积回调', 2, '改挂数后同步调整整流器', inspected)
    return None


def simulate_chemistry_alignment(readings, invalid):
    ph_tenth, bath_c = readings[2], readings[5]
    if invalid.intersection(('ph_tenth', 'bath_c')):
        return None
    if not (ph_tenth>=52 and bath_c>=49):
        return None
    ph_tenth_adjusted = ph_tenth-5
    bath_c_adjusted = bath_c-8
    inspected = {
        'ph_tenth': (ph_tenth, ph_tenth_adjusted),
        'bath_c': (bath_c, bath_c_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('补液后温度核准', 2, '核验相同挂具试镀厚度', inspected)
    return None


def options(values, missing):
    measurements=tuple(values)
    unobserved=frozenset(missing)
    cases=(
        simulate_retune_bath(measurements, unobserved),
        simulate_refresh_bath_solution(measurements, unobserved),
        simulate_cool_soak(measurements, unobserved),
        simulate_reduce_hanger_batch(measurements, unobserved),
        simulate_chemistry_alignment(measurements, unobserved),
    )
    return tuple(action for action in cases if action is not None)
