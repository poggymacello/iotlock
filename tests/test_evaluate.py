import numpy as np

from iotlock.evaluate import centrality_vs_impact, survival_curve, time_to_saturation
from iotlock.topology import build_topology, compute_centrality


def test_time_to_saturation_finds_correct_timestep():
    curve = np.array([1.0, 0.9, 0.7, 0.4, 0.2])
    assert time_to_saturation(curve, threshold=0.5) == 3


def test_time_to_saturation_returns_none_if_never_reached():
    curve = np.array([1.0, 0.95, 0.9, 0.85])
    assert time_to_saturation(curve, threshold=0.5) is None


def test_survival_curve_is_monotonic_non_increasing_on_average():
    graph = build_topology(n_nodes=20, m=2, seed=1)
    curve = survival_curve(graph, "none", n_trials=10, max_timesteps=15, seed=1)
    assert len(curve) == 16
    # failures are permanent, so the averaged survival fraction can never
    # tick back up from one timestep to the next
    assert all(curve[i + 1] <= curve[i] + 1e-9 for i in range(len(curve) - 1))


def test_centrality_vs_impact_shapes_and_correlation_range():
    graph = build_topology(n_nodes=20, m=2, seed=1)
    centrality = compute_centrality(graph)
    centrality_values, impacts, corr = centrality_vs_impact(
        graph, centrality, n_trials=3, max_timesteps=8, seed=1
    )
    assert len(centrality_values) == len(impacts) == graph.number_of_nodes()
    assert -1.0 <= corr <= 1.0
