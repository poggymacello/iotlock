"""Botnet detection over real N-BaIoT traffic: a gradient-boosting
classifier, evaluated with a device-holdout split so the reported
performance reflects generalization to a device type never profiled
during training, not just recognizing traffic patterns from devices
already seen.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler

from iotlock import evaluate as eval_mod
from iotlock import leakage
from iotlock.botnet_data import DEVICES, NBaIoTDataset, device_holdout_split, load_all_devices

MAX_ACCEPTABLE_FPR = (0.01, 0.05)


class BotnetDetector:
    def __init__(self, seed: int = 42) -> None:
        self.scaler = StandardScaler()
        self.model = HistGradientBoostingClassifier(random_state=seed)

    def fit(self, X: np.ndarray, y: np.ndarray) -> BotnetDetector:
        scaled = self.scaler.fit_transform(X)
        self.model.fit(scaled, y)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        scaled = self.scaler.transform(X)
        return self.model.predict_proba(scaled)[:, 1]


def run_detection_pipeline(
    seed: int = 42,
    test_device: str = "SimpleHome_XCS7_1003_WHT_Security_Camera",
    n_per_class: int | None = 3000,
    dataset: NBaIoTDataset | None = None,
) -> dict:
    ds = dataset if dataset is not None else load_all_devices(n_per_class=n_per_class, seed=seed)
    train, test = device_holdout_split(ds, test_device=test_device)

    n_suspicious = leakage.flag_suspicious_feature_count(train.X, train.y)

    detector = BotnetDetector(seed=seed).fit(train.X, train.y)
    scores = detector.predict_proba(test.X)

    m = eval_mod.compute_detection_metrics(test.y, scores)
    metrics = m.as_dict()
    for fpr_budget in MAX_ACCEPTABLE_FPR:
        recall = eval_mod.recall_at_fpr(test.y, scores, fpr_budget)
        metrics[f"recall_at_fpr_{int(fpr_budget * 100)}pct"] = round(recall, 4)
    metrics["bootstrap_pr_auc_ci"] = eval_mod.bootstrap_ci(test.y, scores, seed=seed)
    polarity_flag = eval_mod.polarity_warning(m.roc_auc)

    return {
        "train": train,
        "test": test,
        "detector": detector,
        "scores": scores,
        "metrics": metrics,
        "polarity_flag": polarity_flag,
        "test_device": test_device,
        "base_rates": {"train": float(train.y.mean()), "test": float(test.y.mean())},
        "devices_used": list(DEVICES),
        "n_suspicious_features": n_suspicious,
        "n_features": int(train.X.shape[1]),
    }
