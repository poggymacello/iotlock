"""Loader for real N-BaIoT IoT botnet traffic data.

N-BaIoT (Meidan et al., 2018) captures real network traffic from 9
commercial IoT devices, each infected in a lab by real Mirai and/or
BASHLITE (gafgyt) malware, alongside each device's own pre-infection
benign traffic. This project uses 3 of the 9 devices (see
data/README.md for why: the full 9-device, all-attack-subtype dataset
is ~2.1GB and RAR-compressed; 3 devices spanning different device
types -- a doorbell, a thermostat, a security camera -- with one real
attack subtype from each botnet family is a tractable, still-genuinely-
real subset) and one attack subtype per botnet family (`scan`, chosen
because it's present and comparably sized across all 3 devices).

Every row is a 115-dimensional statistical feature vector (traffic
volume/behavior statistics over several time-decay windows, extracted
by N-BaIoT's own pipeline, documented in the dataset's
`N_BaIoT_dataset_description_v1.txt`) -- there is no raw packet capture
or payload data anywhere in this project.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "nbaiot"

DEVICES = ("Danmini_Doorbell", "Ecobee_Thermostat", "SimpleHome_XCS7_1003_WHT_Security_Camera")


@dataclass(frozen=True)
class NBaIoTDataset:
    X: np.ndarray  # (n_rows, 115)
    y: np.ndarray  # (n_rows,) 0=benign, 1=attack (either botnet family)
    device: np.ndarray  # (n_rows,) device name string
    family: np.ndarray  # (n_rows,) "benign" | "gafgyt" | "mirai"

    def __len__(self) -> int:
        return len(self.y)


def load_device(
    device: str, n_per_class: int | None = 3000, seed: int = 42, raw_dir: Path | None = None
) -> NBaIoTDataset:
    """Loads one device's benign + gafgyt-scan + mirai-scan traffic,
    optionally subsampled (stratified, seeded) to ``n_per_class`` rows
    per class for tractability."""
    directory = (raw_dir or RAW_DIR) / device
    rng = np.random.default_rng(seed)

    frames = []
    for family, filename, label in [
        ("benign", "benign_traffic.csv", 0),
        ("gafgyt", "gafgyt_scan.csv", 1),
        ("mirai", "mirai_scan.csv", 1),
    ]:
        path = directory / filename
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if n_per_class is not None and len(df) > n_per_class:
            idx = rng.choice(df.index.to_numpy(), size=n_per_class, replace=False)
            df = df.loc[idx]
        df = df.copy()
        df["__label"] = label
        df["__family"] = family
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    feature_cols = [c for c in combined.columns if not c.startswith("__")]

    return NBaIoTDataset(
        X=combined[feature_cols].to_numpy(dtype=float),
        y=combined["__label"].to_numpy(),
        device=np.full(len(combined), device),
        family=combined["__family"].to_numpy(),
    )


def load_all_devices(
    devices: tuple[str, ...] = DEVICES,
    n_per_class: int | None = 3000,
    seed: int = 42,
    raw_dir: Path | None = None,
) -> NBaIoTDataset:
    parts = [load_device(d, n_per_class=n_per_class, seed=seed, raw_dir=raw_dir) for d in devices]
    return NBaIoTDataset(
        X=np.concatenate([p.X for p in parts]),
        y=np.concatenate([p.y for p in parts]),
        device=np.concatenate([p.device for p in parts]),
        family=np.concatenate([p.family for p in parts]),
    )


def device_holdout_split(
    dataset: NBaIoTDataset, test_device: str
) -> tuple[NBaIoTDataset, NBaIoTDataset]:
    """Splits by device, not randomly: train on every device except
    ``test_device``, test only on it. A random row-level split would let
    the model see other rows from the *same* device (and its specific
    network/traffic fingerprint) it's tested on; a real deployment
    needs to work on devices it has never profiled before, which is
    exactly what this split tests and a random split would hide.
    """
    train_mask = dataset.device != test_device
    test_mask = ~train_mask

    def subset(mask: np.ndarray) -> NBaIoTDataset:
        return NBaIoTDataset(
            X=dataset.X[mask],
            y=dataset.y[mask],
            device=dataset.device[mask],
            family=dataset.family[mask],
        )

    return subset(train_mask), subset(test_mask)
