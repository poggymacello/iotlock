from pathlib import Path

import networkx as nx
import numpy as np
import pytest
import tomllib
from fastapi.testclient import TestClient

from iotlock import api
from iotlock.artifact import N_FEATURES, build_artifact

rng = np.random.default_rng(42)
TRAIN_X = rng.normal(0, 1, size=(150, N_FEATURES))
TRAIN_Y = rng.integers(0, 2, 150)


@pytest.fixture
def client():
    api._artifact = build_artifact(TRAIN_X, TRAIN_Y, test_device="dummy_device", seed=42)
    api._topologies = {
        "TestGraphSmall": nx.cycle_graph(10),
        "TestGraphMedium": nx.cycle_graph(20),
    }
    yield TestClient(api.app)
    api._artifact = None
    api._topologies = None


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_model_info(client):
    resp = client.get("/model")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == api.__version__
    assert body["test_device"] == "dummy_device"


def test_predict_valid_request(client):
    resp = client.post("/predict", json={"features": list(rng.normal(0, 1, N_FEATURES))})
    assert resp.status_code == 200
    body = resp.json()
    assert 0.0 <= body["score"] <= 1.0
    assert body["predicted_label"] in (0, 1)


def test_predict_rejects_wrong_length(client):
    resp = client.post("/predict", json={"features": [1.0, 2.0, 3.0]})
    assert resp.status_code == 422


def test_get_topologies_respects_env_var_override(monkeypatch):
    # regression test: RAW_DIR is computed relative to the installed
    # package's own file location, which is wrong once packaged (e.g. in
    # the Docker image); IOTLOCK_TOPOLOGY_DIR must override it
    sample_dir = Path(__file__).resolve().parent.parent / "data" / "sample" / "topology_zoo"
    monkeypatch.setenv("IOTLOCK_TOPOLOGY_DIR", str(sample_dir))
    api._topologies = None
    try:
        topologies = api.get_topologies()
        assert len(topologies) > 0
    finally:
        api._topologies = None


def test_topologies_lists_preloaded_graphs(client):
    resp = client.get("/topologies")
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()["topologies"]}
    assert names == {"TestGraphSmall", "TestGraphMedium"}


def test_simulate_valid_request(client):
    resp = client.post(
        "/simulate",
        json={"topology": "TestGraphSmall", "strategy": "none", "n_trials": 2, "max_timesteps": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_nodes"] == 10
    assert len(body["survival_curve_pct"]) == 6  # t=0..5 inclusive
    assert all(0.0 <= v <= 100.0 for v in body["survival_curve_pct"])


def test_simulate_rejects_unknown_topology(client):
    resp = client.post(
        "/simulate", json={"topology": "NotARealTopology", "strategy": "none", "n_trials": 2}
    )
    assert resp.status_code == 404


def test_simulate_rejects_unknown_strategy(client):
    resp = client.post(
        "/simulate", json={"topology": "TestGraphSmall", "strategy": "not_a_strategy"}
    )
    assert resp.status_code == 400


def test_dashboard_serves_html(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<select id=\"topology\">" in resp.text


def test_metrics_endpoint_exposes_prometheus_format(client):
    client.get("/healthz")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "iotlock_requests_total" in resp.text


def test_model_version_matches_pyproject(client):
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with open(pyproject, "rb") as f:
        declared_version = tomllib.load(f)["project"]["version"]

    resp = client.get("/model")
    assert resp.json()["version"] == declared_version
