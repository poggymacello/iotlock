import numpy as np

from iotlock import leakage


def test_single_feature_auc_uninformative_near_half():
    labels = np.array([0, 1] * 50)
    features = np.random.default_rng(0).random((100, 3))
    aucs = leakage.single_feature_auc(features, labels)
    assert all(0.3 < a < 0.7 for a in aucs)


def test_single_feature_auc_flags_circular_feature():
    labels = np.array([0] * 50 + [1] * 50)
    features = np.column_stack([labels.astype(float), np.random.default_rng(1).random(100)])
    aucs = leakage.single_feature_auc(features, labels)
    assert aucs[0] == 1.0


def test_flag_suspicious_feature_count():
    labels = np.array([0] * 50 + [1] * 50)
    features = np.column_stack([labels.astype(float), np.random.default_rng(1).random(100)])
    assert leakage.flag_suspicious_feature_count(features, labels) == 1
