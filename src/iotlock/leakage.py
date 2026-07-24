"""Automated leakage check: single-feature predictive power, for the
N-BaIoT detection component. See README's Leakage Controls for what the
manual investigation found: several individual features exceed the
suspicious threshold, and it's resolved as a real, previously-published
characteristic of scan-flood traffic rather than a data-pipeline leak.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score

SUSPICIOUS_AUC_THRESHOLD = 0.98


def single_feature_auc(features: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """AUC of each feature column alone against the label (max(auc, 1-auc) per column)."""
    n_features = features.shape[1]
    aucs = np.empty(n_features)
    for i in range(n_features):
        values = features[:, i]
        if np.all(values == values[0]):
            aucs[i] = 0.5
            continue
        auc = roc_auc_score(labels, values)
        aucs[i] = max(auc, 1 - auc)
    return aucs


def flag_suspicious_feature_count(
    features: np.ndarray, labels: np.ndarray, threshold: float = SUSPICIOUS_AUC_THRESHOLD
) -> int:
    return int((single_feature_auc(features, labels) > threshold).sum())
