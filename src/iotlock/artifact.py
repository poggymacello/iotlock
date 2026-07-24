"""Versioned model artifact for the deployed N-BaIoT botnet detector."""

from __future__ import annotations

import hashlib
import platform
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn

from iotlock import __version__
from iotlock.botnet_data import RAW_DIR
from iotlock.detection import BotnetDetector

N_FEATURES = 115


def _training_data_hash() -> str:
    if not RAW_DIR.exists():
        return "unavailable (trained without local raw data present)"
    digest = hashlib.sha256()
    for path in sorted(RAW_DIR.rglob("*.csv")):
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                digest.update(chunk)
    return digest.hexdigest()


@dataclass
class ModelArtifact:
    version: str
    trained_at: str
    seed: int
    detector: BotnetDetector
    test_device: str
    n_features: int
    training_data_sha256: str
    library_versions: dict[str, str] = field(default_factory=dict)
    python_version: str = field(default_factory=platform.python_version)

    def score(self, features: list[float]) -> float:
        X = np.array([features])
        return float(self.detector.predict_proba(X)[0])


def build_artifact(
    train_X: np.ndarray, train_y: np.ndarray, test_device: str, seed: int = 42
) -> ModelArtifact:
    detector = BotnetDetector(seed=seed).fit(train_X, train_y)
    return ModelArtifact(
        version=__version__,
        trained_at=datetime.now(timezone.utc).isoformat(),
        seed=seed,
        detector=detector,
        test_device=test_device,
        n_features=N_FEATURES,
        training_data_sha256=_training_data_hash(),
        library_versions={
            "python": platform.python_version(),
            "scikit-learn": sklearn.__version__,
        },
    )


def save_artifact(artifact: ModelArtifact, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, path)


def load_artifact(path: Path) -> ModelArtifact:
    return joblib.load(path)


def artifact_path_for_version(models_dir: Path, version: str | None = None) -> Path:
    version = version or __version__
    return models_dir / f"iotlock-{version}.joblib"
