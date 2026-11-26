from dataclasses import dataclass

FIELDS = {'amps': ('槽电流', 'A', 60, 260),
 'time_sec': ('浸镀历时', 's', 80, 450),
 'ph_tenth': ('实测酸碱度', '0.1pH', 35, 66),
 'area_dm': ('挂件总面积', 'dm²', 25, 183),
 'filter_days': ('溶液滤芯使用', '天', 0, 32),
 'bath_c': ('槽液温度', '℃', 35, 68)}
LIMITS = {'result_max': 10000}


class MeasureIssue(ValueError):
    def __init__(self, field: str, code: str):
        super().__init__(f'{field}:{code}')
        self.field = field
        self.code = code


@dataclass(frozen=True, slots=True)
class PlatebathRecord:
    key: str
    cohort: str
    day: int
    received: int
    revision: int
    result_day: int | None
    outcome: float | None
    observed: bool
    amps: float | None
    time_sec: float | None
    ph_tenth: float | None
    area_dm: float | None
    filter_days: float | None
    bath_c: float | None

    def signature(self):
        return (self.key, self.cohort, self.day, self.revision, self.result_day, self.outcome, self.observed,
                *(getattr(self, key) for key in FIELDS))


@dataclass(frozen=True, slots=True)
class Issue:
    source_row: int
    key: str
    field: str
    code: str

    def evidence(self):
        return {'行号': self.source_row, '单号': self.key, '字段': FIELDS.get(self.field, (self.field,))[0],
                '原因': self.code}


@dataclass(frozen=True, slots=True)
class DecodeResult:
    entries: tuple[PlatebathRecord, ...]
    issues: tuple[Issue, ...]
    source_rows: int
