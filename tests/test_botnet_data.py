from pathlib import Path

import numpy as np

from iotlock.botnet_data import device_holdout_split, load_all_devices, load_device

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample" / "nbaiot"
DEVICES = ("Danmini_Doorbell", "Ecobee_Thermostat", "SimpleHome_XCS7_1003_WHT_Security_Camera")


def test_load_device_has_all_three_classes():
    ds = load_device("Danmini_Doorbell", n_per_class=50, raw_dir=SAMPLE_DIR)
    assert set(ds.family.tolist()) == {"benign", "gafgyt", "mirai"}
    assert set(ds.y.tolist()) <= {0, 1}


def test_load_device_respects_subsample_cap():
    ds = load_device("Danmini_Doorbell", n_per_class=10, raw_dir=SAMPLE_DIR)
    # 3 classes x at most 10 rows each
    assert len(ds) <= 30


def test_load_all_devices_combines_every_device():
    ds = load_all_devices(devices=DEVICES, n_per_class=20, raw_dir=SAMPLE_DIR)
    assert set(ds.device.tolist()) == set(DEVICES)
    assert not np.isnan(ds.X).any()


def test_device_holdout_split_isolates_test_device():
    ds = load_all_devices(devices=DEVICES, n_per_class=20, raw_dir=SAMPLE_DIR)
    train, test = device_holdout_split(ds, test_device="Ecobee_Thermostat")
    assert set(test.device.tolist()) == {"Ecobee_Thermostat"}
    assert "Ecobee_Thermostat" not in set(train.device.tolist())
    assert len(train) + len(test) == len(ds)
