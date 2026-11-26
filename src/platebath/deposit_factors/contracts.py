from dataclasses import dataclass
from math import isfinite
from ..hanger_tickets.contracts import PlatebathRecord as RawObservation

RAW_KEYS = ('amps', 'time_sec', 'ph_tenth', 'area_dm', 'filter_days', 'bath_c')
FEATURE_KEYS = ('current_density', 'amp_minutes', 'ph_distance', 'filter_load', 'warm_rise')
FEATURE_NAMES = ('平均电流密度', '单位面积安分', '偏离控制点', '滤芯负载', '超温暴露')


@dataclass(frozen=True, slots=True)
class FeatureState:
    fill: tuple[float, ...]
    offsets: tuple[float, ...]
    scales: tuple[float, ...]
    floor: tuple[float, ...]
    ceil: tuple[float, ...]
    fingerprint: str

    def __post_init__(self):
        if len(self.fill) != len(RAW_KEYS):
            raise ValueError('补值向量维数与字段表不匹配')
        if any(len(column) != len(FEATURE_KEYS) for column in (self.offsets, self.scales, self.floor, self.ceil)):
            raise ValueError('特征状态维数不匹配')
        if min(self.scales) <= 0:
            raise ValueError('特征尺度必须为正')


@dataclass(frozen=True, slots=True)
class FeatureVector:
    key: str
    cohort: str
    day: int
    values: tuple[float, ...]
    factors: tuple[float, ...]
    missing: tuple[str, ...]
    excursions: tuple[str, ...]
    outcome: float | None
    observed: bool
    input_values: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class PreparedRuns:
    train: tuple[FeatureVector, ...]
    calibration: tuple[FeatureVector, ...]
    replay: tuple[FeatureVector, ...]
    live: tuple[FeatureVector, ...]

    def segments(self):
        return tuple((name, getattr(self, name)) for name in ('train', 'calibration', 'replay', 'live'))


@dataclass(frozen=True, slots=True)
class Proposal:
    name: str
    field: str
    before: float
    after: float
    work: int

    def __post_init__(self):
        if self.before == self.after or not isfinite(self.after) or self.work < 0:
            raise ValueError('推演动作需要实质变动和有效额度')

    def evidence(self):
        return {'情形': self.name, '变更项': self.field, '原值': self.before,
                '置换值': self.after, '用量': self.work}

@dataclass(frozen=True, slots=True)
class DepositFactors:
    current_flux: float
    coulomb_area: float
    warm_minutes: float
    ph_alkali: float
    ph_acid: float
    bath_service: float
    area_minutes: float
    current_headroom: float

    def __post_init__(self):
        if not all(isfinite(amount) for amount in (self.current_flux, self.coulomb_area, self.warm_minutes, self.ph_alkali, self.ph_acid, self.bath_service, self.area_minutes, self.current_headroom)):
            raise ValueError('挂具批存在无效的作业量测')

    def explain(self, labels=None):
        return (
            ('挂件电流密度', round(self.current_flux, 4)),
            ('每平方分米库仑', round(self.coulomb_area, 4)),
            ('高于基准的温时', round(self.warm_minutes, 4)),
            ('高酸碱度方向', round(self.ph_alkali, 4)),
            ('低酸碱度方向', round(self.ph_acid, 4)),
            ('滤芯剩余巡查天数', round(self.bath_service, 4)),
            ('挂具面积浸镀积', round(self.area_minutes, 4)),
            ('工艺电流裕量', round(self.current_headroom, 4)),
        )
