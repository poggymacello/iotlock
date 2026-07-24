from pathlib import Path

from iotlock.botnet_data import DEVICES, load_all_devices
from iotlock.detection import run_detection_pipeline

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample" / "nbaiot"


def _sample_dataset():
    return load_all_devices(devices=DEVICES, n_per_class=30, raw_dir=SAMPLE_DIR)


def test_run_detection_pipeline_produces_metrics():
    result = run_detection_pipeline(seed=1, dataset=_sample_dataset())
    m = result["metrics"]
    assert 0.0 <= m["roc_auc"] <= 1.0
    assert 0.0 <= m["pr_auc"] <= 1.0
    assert "recall_at_fpr_1pct" in m
    assert "recall_at_fpr_5pct" in m
    assert "bootstrap_pr_auc_ci" in m


def test_run_detection_pipeline_holds_out_test_device():
    result = run_detection_pipeline(
        seed=1, test_device="Ecobee_Thermostat", dataset=_sample_dataset()
    )
    assert set(result["test"].device.tolist()) == {"Ecobee_Thermostat"}


def test_run_detection_pipeline_reports_base_rates():
    result = run_detection_pipeline(seed=1, dataset=_sample_dataset())
    assert 0.0 <= result["base_rates"]["train"] <= 1.0
    assert 0.0 <= result["base_rates"]["test"] <= 1.0
