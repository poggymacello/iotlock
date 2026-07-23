"""Barabási-Albert scale-free IoT network topology and centrality analysis.

Real IoT/internet-like networks tend to be scale-free: most devices have few
connections, but a small number of hub-like nodes (gateways, aggregation
points) have many. A Barabási-Albert graph reproduces that degree
distribution via preferential attachment, which is a much closer structural
match for an IoT network than a uniformly random graph, where every node
has roughly the same number of connections and there are no real hubs to
reason about.
"""

from __future__ import annotations

import networkx as nx


def build_topology(n_nodes: int = 40, m: int = 2, seed: int = 42) -> nx.Graph:
    """``m`` is the number of edges each new node attaches with (Barabási-Albert parameter)."""
    return nx.barabasi_albert_graph(n_nodes, m, seed=seed)


def compute_centrality(graph: nx.Graph) -> dict[int, float]:
    """Betweenness centrality: how often a node sits on the shortest path between others."""
    return nx.betweenness_centrality(graph)
