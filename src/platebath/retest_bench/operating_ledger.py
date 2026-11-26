from collections import defaultdict
from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True, slots=True)
class GaugeCoupon:
    hanger: str
    density: float
    dose: float
    corrected_acidity: float
    filter_life: float
    estimate_um: float
    disposition: str

    @property
    def electrolyte_band(self):
        if self.corrected_acidity < 4.5:
            return '偏酸'
        if self.corrected_acidity > 5.8:
            return '偏高'
        return '中段'


def coupon_for(hanger):
    reading = hanger['measurements']
    amperes = reading['amps']
    area = reading['area_dm']
    ph = reading['ph_tenth'] / 10
    heat = reading['bath_c'] - 50
    return GaugeCoupon(hanger['key'], amperes / area, amperes * reading['time_sec'] / (60 * area),
                       ph - .012 * heat, reading['filter_days'], hanger['estimate'], hanger['state'])


def target_gauge_points(coupon, median_dose):
    high_load = coupon.dose > median_dose * 1.25
    aging = coupon.filter_life >= 24
    if coupon.density > 4.4:
        return ('前端凸缘', '迎流侧', '基材遮蔽角')
    if coupon.electrolyte_band != '中段' and aging:
        return ('中轴', '回液侧', '槽底随件试片')
    if high_load:
        return ('挂尖', '中轴')
    if coupon.estimate_um >= 2.3:
        return ('回液侧', '盲槽孔缘')
    return ('中轴',)


def operating_ledger(rows):
    vats = defaultdict(list)
    reports = []
    for hanger in rows:
        if hanger['unmeasured']:
            reports.append({'业务安排': '补测电镀参数', '关联单据': hanger['key'], '槽位': hanger['zone']})
        else:
            vats[hanger['zone']].append(coupon_for(hanger))
    for tank, coupons in sorted(vats.items()):
        median_dose = median(item.dose for item in coupons)
        queued = 0
        actual = 0
        for item in sorted(coupons, key=lambda value: (-value.density, value.hanger)):
            points = target_gauge_points(item, median_dose)
            if item.disposition == '观察' and len(points) == 1:
                continue
            if item.disposition == '已分派':
                actual += len(points)
            else:
                queued += len(points)
            reports.append({'业务安排': '见证片复测' if item.density <= 4.4 else '超流挂件隔离',
                            '关联单据': item.hanger, '槽位': tank, '电流密度': round(item.density, 2),
                            '折温后酸碱度': round(item.corrected_acidity, 2), '应测位置': '、'.join(points)})
        reports.append({'业务安排': '测厚仪负荷', '槽位': tank, '中位面电荷': round(median_dose, 2),
                        '已排测点': actual, '待核测点': queued, '挂次': len(coupons)})
    return reports
