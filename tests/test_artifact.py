from pathlib import Path

import numpy as np

from iotlock.artifact import artifact_path_for_version, build_artifact, load_artifact, save_artifact

rng = np.random.default_rng(42)
TRAIN_X = rng.normal(0, 1, size=(150, 115))
TRAIN_Y = rng.integers(0, 2, 150)


def test_build_artifact_scores_are_probabilities():
    artifact = build_artifact(TRAIN_X, TRAIN_Y, test_device="dummy_device", seed=42)
    score = artifact.score(list(rng.normal(0, 1, 115)))
    assert 0.0 <= score <= 1.0


def test_artifact_round_trips_through_disk(tmp_path):
    artifact = build_artifact(TRAIN_X, TRAIN_Y, test_device="dummy_device", seed=42)
    path = tmp_path / "test.joblib"
    save_artifact(artifact, path)
    assert path.exists()

    loaded = load_artifact(path)
    assert loaded.version == artifact.version
    features = list(rng.normal(0, 1, 115))
    assert loaded.score(features) == artifact.score(features)


def test_artifact_path_for_version():
    path = artifact_path_for_version(Path("models"), version="9.9.9")
    assert path == Path("models") / "iotlock-9.9.9.joblib"


def test_artifact_records_test_device():
    artifact = build_artifact(TRAIN_X, TRAIN_Y, test_device="Ecobee_Thermostat", seed=42)
    assert artifact.test_device == "Ecobee_Thermostat"
    assert artifact.n_features == 115
