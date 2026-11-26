from collections import defaultdict
from math import fabs, fsum
from statistics import mean, median

from .tree_model import score_kernel


def power_group(hanger):
    amps, _, _, area, *_ = hanger.input_values
    basis = amps/area
    return 0 if basis<1.8 else 1 if basis<2.7 else 2


def existing_control_line(hangers):
    within = defaultdict(list)
    for hook in hangers:
        within[power_group(hook)].append(hook.outcome)
    return {density:mean(thickness) for density,thickness in within.items()},mean(hook.outcome for hook in hangers)


def check_density_standard(levels,hanger):
    plants, default = levels
    return plants.get(power_group(hanger),default)


def baseline_review(fit, training, replay):
    convention = existing_control_line(training)
    production = defaultdict(list)
    for sample in replay:
        if not sample.observed or sample.outcome is None:
            continue
        estimate, _ = score_kernel(fit.parameters,sample)
        baseline = check_density_standard(convention, sample)
        actual = sample.outcome
        loss, prior = abs(actual-estimate),abs(actual-baseline)
        production[sample.cohort].append((loss,prior,estimate-actual,baseline-actual))
    reports = []
    for sector, comparison in sorted(production.items()):
        model_loss, base_loss, error, original = zip(*comparison,strict=True)
        paired = tuple(old-new for old,new in zip(base_loss,model_loss,strict=True))
        n = len(comparison)
        reports.append({'回放组':sector,'实绩数':n,'基线':'按电流密度三级均值','估计代价':round(mean(model_loss),4),
                        '业务基线代价':round(mean(base_loss),4),'模型偏误中位':round(median(error),4),
                        '参照偏误中位':round(median(original),4),'同单误差减少中位':round(median(paired),4),
                        '改善单数':sum(delta>0 for delta in paired),'恶化单数':sum(delta<0 for delta in paired)})
    return reports
