from pathlib import Path

from iotlock.mitigation_real_pipeline import (
    run_centrality_impact_across_topologies,
    run_mitigation_across_topologies,
)
from iotlock.simulation import STRATEGIES
from iotlock.topology_real import load_topologies

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample" / "topology_zoo"


def _sample_topologies():
    return load_topologies(min_nodes=10, max_nodes=40, raw_dir=SAMPLE_DIR)


def test_run_mitigation_across_topologies_covers_every_strategy():
    result = run_mitigation_across_topologies(_sample_topologies(), n_trials=3, max_timesteps=10)
    assert result["n_topologies"] > 0
    assert set(result["survival_distribution_pct"].keys()) == set(STRATEGIES)
    for dist in result["survival_distribution_pct"].values():
        assert 0.0 <= dist["p50"] <= 100.0


def test_run_centrality_impact_across_topologies_returns_distribution():
    result = run_centrality_impact_across_topologies(
        _sample_topologies(), n_trials=2, max_timesteps=6
    )
    assert result["n_topologies_with_valid_correlation"] > 0
    dist = result["correlation_distribution"]
    assert dist["p50"] is not None
    assert len(result["per_topology_correlation"]) == result["n_topologies_with_valid_correlation"]
