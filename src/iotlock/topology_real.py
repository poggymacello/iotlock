"""Loader for real network topologies from the Internet Topology Zoo.

The original topology-zoo.org site has gone offline; this project fetches
the GraphML archive from the actively-maintained long-term mirror
(`mroughan/InternetTopologyZoo` on GitHub, run by one of the original
paper's co-authors) instead -- see data/README.md for the live-check that
led to that choice and the full citation.

Real topologies vary hugely in size (a handful of nodes up to 750+ for
the largest backbone networks), so this module filters to a size band
that keeps the Monte Carlo simulation both meaningful (large enough to
have real structure) and tractable (small enough to run hundreds of
trials across hundreds of topologies quickly), and drops disconnected
graphs -- a cascade/survival simulation on a graph with isolated
components doesn't mean the same thing a connected-network simulation
does.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx

RAW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "topology_zoo"

DEFAULT_MIN_NODES = 15
DEFAULT_MAX_NODES = 150


def load_topologies(
    min_nodes: int = DEFAULT_MIN_NODES,
    max_nodes: int = DEFAULT_MAX_NODES,
    raw_dir: Path | None = None,
) -> list[tuple[str, nx.Graph]]:
    """Loads every .graphml file in ``raw_dir``, keeping only connected
    graphs with ``min_nodes`` <= n <= ``max_nodes`` nodes. Returns a list
    of (topology_name, graph) sorted by name for determinism.
    """
    directory = raw_dir or RAW_DIR
    graphs = []
    for path in sorted(directory.glob("*.graphml")):
        try:
            raw = nx.read_graphml(path)
        except Exception:  # noqa: BLE001  # nosec B112 -- a few Topology Zoo files are malformed XML, safely skipped
            continue
        graph = nx.Graph(raw.to_undirected())
        graph.remove_edges_from(nx.selfloop_edges(graph))

        if not (min_nodes <= graph.number_of_nodes() <= max_nodes):
            continue
        if not nx.is_connected(graph):
            continue

        graphs.append((path.stem, graph))
    return graphs
