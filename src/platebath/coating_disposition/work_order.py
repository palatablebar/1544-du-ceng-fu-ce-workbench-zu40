def collect_gauge_zero(measures, missing, estimate):
    time_sec = measures['time_sec']
    if not (time_sec>=220):
        return None
    value=time_sec/60
    return {'现场复核':'回零','可复查值':round(value,3),'单位':'分钟','归档要求':'同面两点测厚前先回零',
            '需补测':not set(missing).isdisjoint(('time_sec',))}


def collect_deposited_charge(measures, missing, estimate):
    amps = measures['amps']
    time_sec = measures['time_sec']
    area_dm = measures['area_dm']
    if not (amps/area_dm>=2.7):
        return None
    value=amps*time_sec/area_dm
    return {'现场复核':'记录电荷','可复查值':round(value,3),'单位':'库仑/dm²','归档要求':'将电源与挂具单的读数写入复测票',
            '需补测':not set(missing).isdisjoint(('amps', 'time_sec', 'area_dm'))}


def collect_filter_log(measures, missing, estimate):
    filter_days = measures['filter_days']
    if not (filter_days>=15):
        return None
    value=filter_days
    return {'现场复核':'抄滤芯','可复查值':round(value,3),'单位':'天','归档要求':'找到本批过滤器领用时间',
            '需补测':not set(missing).isdisjoint(('filter_days',))}


def collect_bath_sample(measures, missing, estimate):
    ph_tenth = measures['ph_tenth']
    bath_c = measures['bath_c']
    if not (abs(ph_tenth-49)>=7 or bath_c>=60):
        return None
    value=ph_tenth/10
    return {'现场复核':'确认槽液','可复查值':round(value,3),'单位':'pH','归档要求':'测完留存同批温度和酸碱样',
            '需补测':not set(missing).isdisjoint(('ph_tenth', 'bath_c'))}


def check_coating_disposition(records):
    guide = []
    for ticket in records:
        if ticket['state'] not in ('已分派','暂停','人工判读'):
            continue
        measures=ticket['measurements']
        absent=ticket['unmeasured']
        estimate=ticket['estimate']
        checks = (
            collect_gauge_zero(measures,absent,estimate),
            collect_deposited_charge(measures,absent,estimate),
            collect_filter_log(measures,absent,estimate),
            collect_bath_sample(measures,absent,estimate),
        )
        required=tuple(check for check in checks if check is not None)
        if not required:
            continue
        review=ticket['key']
        for check in required:
            guide.append({'签收单':review,'作业区':ticket['zone'],'处置':ticket['state'],**check})
    return guide
