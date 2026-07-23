import networkx as nx

from iotlock.topology import build_topology, compute_centrality


def test_topology_is_connected_and_has_right_node_count():
    graph = build_topology(n_nodes=30, m=2, seed=1)
    assert graph.number_of_nodes() == 30
    assert nx.is_connected(graph)  # Barabási-Albert graphs are always connected


def test_topology_is_scale_free_not_uniform_degree():
    # a Barabási-Albert graph should have a few high-degree hubs and many
    # low-degree nodes, unlike a random graph where degree is roughly uniform
    graph = build_topology(n_nodes=60, m=2, seed=1)
    degrees = [d for _, d in graph.degree()]
    assert max(degrees) > 3 * (sum(degrees) / len(degrees))  # hub(s) far above average


def test_centrality_returns_a_value_per_node():
    graph = build_topology(n_nodes=20, m=2, seed=1)
    centrality = compute_centrality(graph)
    assert set(centrality.keys()) == set(graph.nodes())
    assert all(0.0 <= v <= 1.0 for v in centrality.values())
