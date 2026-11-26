from dataclasses import dataclass
from math import fsum


@dataclass(frozen=True)
class Node:
    prediction: float
    sample_size: int
    feature: int | None = None
    threshold: float | None = None
    under: 'Node | None' = None
    above: 'Node | None' = None


def impurity(sample):
    center = fsum(sample) / len(sample)
    return fsum((value - center) ** 2 for value in sample)


def cuts(rows, minimum):
    for field in range(len(rows[0].values)):
        sorted_rows = sorted(rows, key=lambda ticket: (ticket.values[field], ticket.key))
        for index in range(minimum, len(rows) - minimum + 1):
            before, after = sorted_rows[index - 1:index + 1]
            if before.values[field] == after.values[field]:
                continue
            pivot = (before.values[field] + after.values[field]) / 2
            yield field, pivot, sorted_rows[:index], sorted_rows[index:]


def grow(rows, depth=0):
    targets = [ticket.outcome for ticket in rows]
    centre = fsum(targets) / len(targets)
    parent_error = impurity(targets)
    if depth >= 3 or len(rows) < 14 or parent_error < 1e-10:
        return Node(centre, len(rows))
    best = None
    for feature, pivot, below, above in cuts(rows, 7):
        squared = impurity([row.outcome for row in below]) + impurity([row.outcome for row in above])
        candidate = (squared, feature, pivot, below, above)
        if best is None or candidate[:3] < best[:3]:
            best = candidate
    if best is None or best[0] > parent_error * .96:
        return Node(centre, len(rows))
    _, feature, cutoff, low, high = best
    return Node(centre, len(rows), feature, cutoff, grow(low, depth+1), grow(high, depth+1))


def leaves(root):
    if root.feature is None:
        return 1
    return leaves(root.under) + leaves(root.above)


def fit_kernel(rows):
    root = grow(rows)
    return root, (('复测树叶子', leaves(root)), ('根节点厚差', root.prediction))


def score_kernel(root, sample):
    path_impacts = [0.0] * len(sample.values)
    while root.feature is not None:
        next_node = root.under if sample.values[root.feature] <= root.threshold else root.above
        path_impacts[root.feature] += next_node.prediction - root.prediction
        root = next_node
    return root.prediction, tuple(path_impacts)
