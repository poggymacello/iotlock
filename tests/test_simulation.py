import pytest

from iotlock.simulation import simulate_cascade
from iotlock.topology import build_topology


def test_history_length_and_shape():
    graph = build_topology(n_nodes=15, m=2, seed=1)
    history = simulate_cascade(graph, strategy="none", max_timesteps=10, seed=1)
    assert len(history) == 11  # includes t=0
    for state in history:
        assert set(state.keys()) == set(graph.nodes())


def test_failures_are_permanent_once_triggered():
    graph = build_topology(n_nodes=15, m=2, seed=1)
    history = simulate_cascade(graph, strategy="none", max_timesteps=15, seed=1)
    for node in graph.nodes():
        failed_at = [t for t, state in enumerate(history) if state[node]]
        if failed_at:
            first_fail = failed_at[0]
            assert all(history[t][node] for t in range(first_fail, len(history)))


def test_isolate_failed_removes_cascade_effect():
    # with cascading disabled, isolate_failed should never show MORE total
    # failures than "none" on the same seed, since "none" has every failure
    # cause "isolate_failed" has, plus cascading on top
    graph = build_topology(n_nodes=30, m=2, seed=2)
    history_none = simulate_cascade(graph, strategy="none", max_timesteps=20, seed=5)
    history_isolated = simulate_cascade(graph, strategy="isolate_failed", max_timesteps=20, seed=5)

    total_none = sum(history_none[-1].values())
    total_isolated = sum(history_isolated[-1].values())
    assert total_isolated <= total_none


def test_unknown_strategy_raises():
    graph = build_topology(n_nodes=10, m=2, seed=1)
    with pytest.raises(ValueError):
        simulate_cascade(graph, strategy="not-a-real-strategy")


def test_start_node_begins_failed():
    graph = build_topology(n_nodes=10, m=2, seed=1)
    history = simulate_cascade(graph, strategy="none", max_timesteps=5, seed=1, start_node=3)
    assert history[0][3] is True
