from dataclasses import dataclass, replace

RISK_CUTOFF = 2.3


@dataclass(frozen=True, slots=True)
class Policy:
    capacity: int
    group_quota: int
    trigger: float

    @classmethod
    def select(cls, capacity, mode):
        if type(capacity) is not int or not 1 <= capacity <= 60:
            raise ValueError('本班额度须在 1 至 60 之间')
        if mode == 'balanced':
            per_group = max(3, (capacity*3 + 4)//5)
            return cls(capacity, per_group, RISK_CUTOFF)
        if mode == 'focus':
            return cls(capacity, capacity, RISK_CUTOFF * .92)
        raise ValueError('未知复核策略')


@dataclass(frozen=True, slots=True)
class RuleNotice:
    rule_id: str
    meaning: str
    hard: bool = False


@dataclass(frozen=True, slots=True)
class Job:
    key: str
    cohort: str
    estimate: float
    lower: float | None
    upper: float | None
    cost: int
    state: str
    reason: str
    summary: str
    priority: float
    rule_hits: tuple[str, ...]
    probability: float | None = None

    @property
    def risk_probability(self):
        return self.probability

    @property
    def overrun_probability(self):
        return self.probability

    @property
    def over_line_probability(self):
        return self.probability

    @property
    def risk(self):
        return self.probability

    @property
    def chance(self):
        return self.probability

    def change(self, state, reason, summary):
        return replace(self, state=state, reason=reason, summary=summary)


@dataclass(frozen=True, slots=True)
class Plan:
    jobs: tuple[Job, ...]
    capacity: int
    balance: int
    used_by_group: tuple[tuple[str, int], ...]
    expected_hits: float = 0.0
    risk_ready: bool = True

    @property
    def expected_overrun_hits(self):
        return self.expected_hits

    @property
    def total_probability(self):
        return self.expected_hits

    @property
    def expected_value(self):
        return self.expected_hits

    @property
    def probabilities(self):
        return {job.key: job.probability for job in self.jobs if job.probability is not None}

    @property
    def risk_probabilities(self):
        return self.probabilities

    @property
    def probability_by_key(self):
        return self.probabilities

    def probability_for(self, key):
        return self.probabilities.get(key)
