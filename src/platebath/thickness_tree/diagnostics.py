from math import exp, log, fsum, sqrt
from statistics import median, mean, quantiles

from .tree_model import score_kernel



def explain_thickness_tree(fit, calibration, replay, live):
    tree = fit.parameters
    measure = ('电流密度','单位面积安分','酸碱偏差','过滤负载','温度暴露')
    queue = [('根',tree)]
    lines = []
    while queue:
        branch, leaf = queue.pop(0)
        if leaf.feature is None:
            lines.append({'厚差路径':branch,'挂具样本':leaf.sample_size,'估计厚差': round(leaf.prediction,3)})
            continue
        expression = f'{measure[leaf.feature]} 标准值 {leaf.threshold:.2f}'
        queue.append((f'{branch} / {expression} 以下',leaf.under))
        queue.append((f'{branch} / {expression} 以上',leaf.above))
    return lines
