from pathlib import Path

import networkx as nx

from iotlock.topology_real import load_topologies

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample" / "topology_zoo"


def test_load_topologies_returns_connected_graphs_in_range():
    graphs = load_topologies(min_nodes=10, max_nodes=40, raw_dir=SAMPLE_DIR)
    assert len(graphs) > 0
    for name, graph in graphs:
        assert isinstance(name, str)
        assert nx.is_connected(graph)
        assert 10 <= graph.number_of_nodes() <= 40


def test_load_topologies_respects_size_filter():
    wide = load_topologies(min_nodes=1, max_nodes=1000, raw_dir=SAMPLE_DIR)
    narrow = load_topologies(min_nodes=25, max_nodes=30, raw_dir=SAMPLE_DIR)
    assert len(narrow) <= len(wide)
    for _, graph in narrow:
        assert 25 <= graph.number_of_nodes() <= 30


def test_load_topologies_no_self_loops():
    graphs = load_topologies(min_nodes=10, max_nodes=40, raw_dir=SAMPLE_DIR)
    for _, graph in graphs:
        assert nx.number_of_selfloops(graph) == 0


def test_load_topologies_sorted_by_name():
    graphs = load_topologies(min_nodes=10, max_nodes=40, raw_dir=SAMPLE_DIR)
    names = [name for name, _ in graphs]
    assert names == sorted(names)
