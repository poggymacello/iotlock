"""FastAPI service: the N-BaIoT botnet detector (`POST /predict`) and an
interactive "what-if" mitigation dashboard over real Topology Zoo
networks (`GET /dashboard`, backed by `POST /simulate`).

Everything here remains pure defensive simulation and detection --
`/simulate` runs the same cascade model used throughout this project on
a real network's *topology* (nodes and links only, no live traffic, no
real infrastructure contacted), and `/predict` scores a caller-supplied
115-dimensional feature vector against the trained detector. Neither
endpoint sends, floods, or otherwise touches a real network.

Security notes (see SECURITY.md for the full policy):
- `/simulate`'s topology name is validated against a fixed, preloaded
  allowlist (the actual Topology Zoo graphs this service loaded at
  startup) -- it can't be used to make the server read an arbitrary
  file path.
- Rate limiting caps how fast a single client can call either endpoint.
- Request metadata (status, latency) is logged; detection feature
  values are not.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from iotlock import __version__
from iotlock.artifact import N_FEATURES, ModelArtifact, artifact_path_for_version, load_artifact
from iotlock.evaluate import survival_curve
from iotlock.simulation import STRATEGIES
from iotlock.topology_real import RAW_DIR as DEFAULT_TOPOLOGY_DIR
from iotlock.topology_real import load_topologies

logger = logging.getLogger("iotlock.api")
logging.basicConfig(level=logging.INFO)

REQUEST_COUNT = Counter("iotlock_requests_total", "Total requests", ["endpoint", "status"])
PREDICT_LATENCY = Histogram("iotlock_predict_latency_seconds", "Predict latency")
SIMULATE_LATENCY = Histogram("iotlock_simulate_latency_seconds", "Simulate latency")

MAX_SIMULATE_TRIALS = 30
MAX_SIMULATE_TIMESTEPS = 40

_RATE_LIMIT = os.environ.get("IOTLOCK_RATE_LIMIT", "60/minute")
limiter = Limiter(key_func=get_remote_address, default_limits=[_RATE_LIMIT])

app = FastAPI(title="IoTLock", version=__version__)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_artifact: ModelArtifact | None = None
_topologies: dict[str, object] | None = None


def get_artifact() -> ModelArtifact:
    global _artifact
    if _artifact is None:
        model_path = Path(
            os.environ.get("IOTLOCK_MODEL_PATH", str(artifact_path_for_version(Path("models"))))
        )
        _artifact = load_artifact(model_path)
        logger.info(
            "loaded model artifact version=%s trained_at=%s",
            _artifact.version,
            _artifact.trained_at,
        )
    return _artifact


def get_topologies() -> dict[str, object]:
    global _topologies
    if _topologies is None:
        # topology_real.RAW_DIR is computed relative to the installed
        # package's own file location, which is wrong once packaged (e.g.
        # inside the Docker image, where the real data lives under /app,
        # not under site-packages) -- this env var is how a deployment
        # points the service at wherever it actually put the topology
        # files, the same pattern used for IOTLOCK_MODEL_PATH.
        topo_dir = Path(os.environ.get("IOTLOCK_TOPOLOGY_DIR", str(DEFAULT_TOPOLOGY_DIR)))
        _topologies = dict(load_topologies(raw_dir=topo_dir))
        logger.info("loaded %d topologies for the dashboard from %s", len(_topologies), topo_dir)
    return _topologies


class PredictRequest(BaseModel):
    features: list[float] = Field(min_length=N_FEATURES, max_length=N_FEATURES)


class PredictResponse(BaseModel):
    score: float
    predicted_label: int
    model_version: str


class SimulateRequest(BaseModel):
    topology: str
    strategy: str
    n_trials: int = Field(default=10, ge=1, le=MAX_SIMULATE_TRIALS)
    max_timesteps: int = Field(default=20, ge=1, le=MAX_SIMULATE_TIMESTEPS)


class SimulateResponse(BaseModel):
    topology: str
    strategy: str
    n_nodes: int
    survival_curve_pct: list[float]


@app.middleware("http")
async def _timing_and_metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    REQUEST_COUNT.labels(endpoint=request.url.path, status=response.status_code).inc()
    if request.url.path == "/predict":
        PREDICT_LATENCY.observe(elapsed)
    elif request.url.path == "/simulate":
        SIMULATE_LATENCY.observe(elapsed)
    logger.info(
        "request path=%s status=%s latency_ms=%.2f",
        request.url.path,
        response.status_code,
        elapsed * 1000,
    )
    return response


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/model")
def model_info() -> dict:
    artifact = get_artifact()
    return {
        "version": artifact.version,
        "trained_at": artifact.trained_at,
        "seed": artifact.seed,
        "test_device": artifact.test_device,
        "n_features": artifact.n_features,
        "training_data_sha256": artifact.training_data_sha256,
        "library_versions": artifact.library_versions,
    }


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict", response_model=PredictResponse)
@limiter.limit(_RATE_LIMIT)
def predict(request: Request, body: PredictRequest) -> PredictResponse:
    artifact = get_artifact()
    threshold = 0.5

    with PREDICT_LATENCY.time():
        score = artifact.score(body.features)

    logger.info("predict served score=%.4f", score)  # feature values never logged
    return PredictResponse(
        score=score, predicted_label=int(score >= threshold), model_version=artifact.version
    )


@app.get("/topologies")
def list_topologies() -> dict[str, list[dict]]:
    topologies = get_topologies()
    return {
        "topologies": [
            {"name": name, "n_nodes": graph.number_of_nodes(), "n_edges": graph.number_of_edges()}
            for name, graph in sorted(topologies.items())
        ]
    }


@app.post("/simulate", response_model=SimulateResponse)
@limiter.limit(_RATE_LIMIT)
def simulate(request: Request, body: SimulateRequest) -> SimulateResponse:
    topologies = get_topologies()
    if body.topology not in topologies:
        raise HTTPException(status_code=404, detail=f"unknown topology {body.topology!r}")
    if body.strategy not in STRATEGIES:
        raise HTTPException(status_code=400, detail=f"unknown strategy {body.strategy!r}")

    graph = topologies[body.topology]
    with SIMULATE_LATENCY.time():
        curve = survival_curve(
            graph, body.strategy, n_trials=body.n_trials, max_timesteps=body.max_timesteps
        )

    return SimulateResponse(
        topology=body.topology,
        strategy=body.strategy,
        n_nodes=graph.number_of_nodes(),
        survival_curve_pct=[round(float(v) * 100, 2) for v in curve],
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return _DASHBOARD_HTML


_DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>IoTLock -- mitigation what-if dashboard</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; }
  select, button { font-size: 1rem; padding: 0.4rem; margin-right: 0.5rem; }
  #chart { border: 1px solid #ccc; margin-top: 1rem; }
  #status { color: #666; margin-top: 0.5rem; }
  .note { font-size: 0.85rem; color: #666; margin-top: 1.5rem; }
</style>
</head>
<body>
<h1>IoTLock: mitigation what-if</h1>
<p>Pick a real network topology (Internet Topology Zoo) and a defensive
strategy, then run the same cascade simulation used in this project's
README against it. Pure simulation -- no real traffic or infrastructure
is touched.</p>
<div>
  <select id="topology"></select>
  <select id="strategy">
    <option value="none">none</option>
    <option value="rate_limit">rate_limit</option>
    <option value="isolate_failed">isolate_failed</option>
  </select>
  <button id="run">Run simulation</button>
</div>
<div id="status"></div>
<canvas id="chart" width="680" height="360"></canvas>
<p class="note">Survival curve = % of nodes still alive at each timestep,
averaged over the requested number of Monte Carlo trials.</p>
<script>
async function loadTopologies() {
  const res = await fetch('/topologies');
  const data = await res.json();
  const select = document.getElementById('topology');
  for (const t of data.topologies) {
    const opt = document.createElement('option');
    opt.value = t.name;
    opt.textContent = `${t.name} (${t.n_nodes} nodes)`;
    select.appendChild(opt);
  }
}

function drawCurve(curve) {
  const canvas = document.getElementById('chart');
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const w = canvas.width, h = canvas.height, pad = 40;

  ctx.strokeStyle = '#ccc';
  ctx.beginPath();
  ctx.moveTo(pad, pad); ctx.lineTo(pad, h - pad); ctx.lineTo(w - pad, h - pad);
  ctx.stroke();
  ctx.fillStyle = '#333';
  ctx.fillText('100%', 5, pad + 4);
  ctx.fillText('0%', 15, h - pad + 4);
  ctx.fillText('timestep', w / 2 - 20, h - 10);

  ctx.strokeStyle = '#2563eb';
  ctx.lineWidth = 2;
  ctx.beginPath();
  curve.forEach((v, i) => {
    const x = pad + (i / (curve.length - 1)) * (w - 2 * pad);
    const y = pad + (1 - v / 100) * (h - 2 * pad);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

async function runSimulation() {
  const topology = document.getElementById('topology').value;
  const strategy = document.getElementById('strategy').value;
  const status = document.getElementById('status');
  status.textContent = 'running...';
  try {
    const res = await fetch('/simulate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({topology, strategy, n_trials: 15, max_timesteps: 20})
    });
    if (!res.ok) {
      status.textContent = 'error: ' + res.status;
      return;
    }
    const data = await res.json();
    drawCurve(data.survival_curve_pct);
    status.textContent = `${topology} (${data.n_nodes} nodes), ${strategy}: ` +
      `final survival ${data.survival_curve_pct[data.survival_curve_pct.length - 1]}%`;
  } catch (e) {
    status.textContent = 'request failed: ' + e;
  }
}

document.getElementById('run').addEventListener('click', runSimulation);
loadTopologies();
</script>
</body>
</html>
"""
