from dataclasses import dataclass
from math import isfinite
from ..thickness_tree.contracts import Prediction

RISK_MODE = True
OVERRUN_THRESHOLD = 2.3
RISK_CUTOFF = OVERRUN_THRESHOLD


@dataclass(frozen=True, slots=True)
class Verification:
    method: str
    parameters: tuple
    size: int
    positives: int | None

    def __post_init__(self):
        if self.size < 0 or self.positives is not None and not 0 <= self.positives <= self.size:
            raise ValueError('校准回查计数失衡')


@dataclass(frozen=True, slots=True)
class Assessment:
    raw: Prediction
    estimate: float
    lower: float | None
    upper: float | None
    uncertain: bool
    probability: float | None = None

    @property
    def risk_probability(self):
        return self.probability

    @property
    def overrun_probability(self):
        return self.probability


@dataclass(frozen=True, slots=True)
class CalibrationRow:
    index: int
    predicted: float | None
    observed: float | None
    count: int


@dataclass(frozen=True, slots=True)
class RiskCalibration:
    """Mature calibration-window rates for the over-line class.

    Both classes must be present; otherwise ``ready`` is false and dispatch
    falls back to manual review rather than treating a zero sample count as a
    probability of zero or one.
    """

    threshold: float
    size: int
    positives: int
    negatives: int
    rows: tuple[CalibrationRow, ...] = ()
    residual_factors: tuple[float, ...] = ()
    method: str = 'independent_calibration_rate'
    key_rates: tuple[tuple[str, float], ...] = ()

    def __post_init__(self):
        if not isinstance(self.threshold, (int, float)) or not isfinite(self.threshold):
            raise ValueError('超线界限必须为有限数值')
        if self.size < 0 or self.positives < 0 or self.negatives < 0:
            raise ValueError('风险校准计数不能为负')
        if self.positives + self.negatives != self.size:
            raise ValueError('正负校准实绩计数失衡')

    @property
    def ready(self) -> bool:
        return self.positives > 0 and self.negatives > 0

    @property
    def requires_review(self) -> bool:
        return not self.ready

    @property
    def base_rate(self) -> float | None:
        return self.positives / self.size if self.size else None

    @property
    def probabilities(self) -> dict[float, float]:
        return {row.predicted: row.observed for row in self.rows
                if row.predicted is not None and row.observed is not None}

    @property
    def probabilities_by_key(self) -> dict[str, float]:
        return dict(self.key_rates)

    def __getitem__(self, key):
        if isinstance(key, str):
            return self.probabilities_by_key[key]
        return self.probability_for(key)

    def probability_for(self, reference=None, **kwargs):
        estimate = kwargs.get('estimate', reference)
        if not self.ready:
            return None
        value = _reference_estimate(estimate)
        if value is None or not isfinite(value):
            return None
        table = self.probabilities
        if value in table:
            return table[value]
        rounded = round(value, 6)
        for score, probability in table.items():
            if round(score, 6) == rounded:
                return probability
        close = [score for score in table if abs(score-value) <= 1e-7 * max(1.0, abs(score), abs(value))]
        if close:
            return table[min(close, key=lambda score: (abs(score-value), score))]
        if self.residual_factors:
            scale = kwargs.get('scale')
            scale_value = 1.0 if scale is None else float(scale)
            if not isfinite(scale_value) or scale_value <= 0:
                scale_value = 1.0
            boundary = (value-self.threshold)/scale_value
            not_exceed = sum(factor <= boundary for factor in self.residual_factors)
            return not_exceed / len(self.residual_factors)
        if table:
            scores = sorted(table)
            if value <= scores[0]:
                return table[scores[0]]
            if value >= scores[-1]:
                return table[scores[-1]]
            left = max(score for score in scores if score <= value)
            right = min(score for score in scores if score >= value)
            if right == left:
                return table[left]
            share = (value-left)/(right-left)
            return table[left] * (1-share) + table[right] * share
        return None

    def probability(self, reference=None, **kwargs):
        return self.probability_for(reference, **kwargs)

    def __call__(self, reference=None, **kwargs):
        return self.probability_for(reference, **kwargs)


RiskProfile = RiskCalibration
ProbabilityCalibration = RiskCalibration
OverrunRiskCalibration = RiskCalibration


def _reference_estimate(reference):
    if reference is None:
        return None
    if isinstance(reference, (int, float)):
        return float(reference)
    for name in ('estimate', 'score', 'predicted'):
        value = getattr(reference, name, None)
        if isinstance(value, (int, float)) and isfinite(value):
            return float(value)
    raw = getattr(reference, 'raw', None)
    if raw is not None and raw is not reference:
        return _reference_estimate(raw)
    if isinstance(reference, dict):
        for name in ('estimate', 'score', 'predicted'):
            value = reference.get(name)
            if isinstance(value, (int, float)) and isfinite(value):
                return float(value)
    return None


@dataclass(frozen=True, slots=True)
class ModelReport:
    status: str
    count: int
    mae: float | None
    error: float | None
    buckets: tuple[CalibrationRow, ...]
    auxiliary: int | float | None
