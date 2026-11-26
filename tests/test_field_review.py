from platebath.pipeline import preview
from platebath.retest_bench.service import operating_ledger


def note(key, measures, *, zone='甲区', state='已分派', estimate=0, hits=(), missing=()):
    return {'key':key,'zone':zone,'state':state,'estimate':estimate,'hits':hits,
            'unmeasured':missing,'measurements':dict(zip(('amps', 'time_sec', 'ph_tenth', 'area_dm', 'filter_days', 'bath_c'),measures,strict=True))}


def test_field_plan_is_visible_and_references_real_tickets():
    desk = preview()
    plan = desk['sections'][6]
    assert plan['operating_title'] == '挂件测厚安排'
    assert plan['operating_rows']
    scoped = {item['关联单据'] for item in plan['operating_rows'] if '关联单据' in item}
    assert scoped and scoped <= {row['key'] for row in desk['rows']}
    assert all(item['业务安排'] for item in plan['operating_rows'])


def test_excessive_current_requires_three_distinct_gauge_points():
    hanger = note('PL-1',(240,210,47,48,12,53),estimate=3.5,state='暂停')
    reading, tally = operating_ledger([hanger])
    assert reading['业务安排']=='超流挂件隔离'
    assert reading['电流密度']==5
    assert len(set(reading['应测位置'].split('、')))==3
    assert tally['已排测点']==0 and tally['待核测点']==3
