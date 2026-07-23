"""Monte Carlo evaluation of mitigation strategies and a centrality-vs-impact check."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from iotlock.simulation import simulate_cascade


def survival_curve(
    graph: nx.Graph, strategy: str, n_trials: int = 30, max_timesteps: int = 20, seed: int = 42
) -> np.ndarray:
    """Average fraction of nodes still alive at each timestep, across ``n_trials`` random runs."""
    n_nodes = graph.number_of_nodes()
    curves = []
    for trial in range(n_trials):
        history = simulate_cascade(
            graph, strategy=strategy, max_timesteps=max_timesteps, seed=seed + trial
        )
        alive_fraction = [1 - sum(state.values()) / n_nodes for state in history]
        curves.append(alive_fraction)
    return np.mean(curves, axis=0)


def time_to_saturation(curve: np.ndarray, threshold: float = 0.5) -> int | None:
    """First timestep where the alive fraction drops below ``threshold``, or None."""
    for t, alive in enumerate(curve):
        if alive < threshold:
            return t
    return None


def centrality_vs_impact(
    graph: nx.Graph,
    centrality: dict[int, float],
    n_trials: int = 6,
    max_timesteps: int = 15,
    seed: int = 42,
) -> tuple[list[float], list[float], float]:
    """Force each node to fail first (strategy="none") and measure total cascade failures caused.

    Returns (centrality_values, impacts, pearson_correlation) so the
    "central nodes are more critical" hypothesis can be checked
    empirically rather than just asserted.
    """
    nodes = list(graph.nodes())
    impacts = []
    for node in nodes:
        totals = []
        for trial in range(n_trials):
            history = simulate_cascade(
                graph,
                strategy="none",
                max_timesteps=max_timesteps,
                seed=seed + trial,
                start_node=node,
            )
            totals.append(sum(history[-1].values()))
        impacts.append(float(np.mean(totals)))

    centrality_values = [centrality[n] for n in nodes]
    corr = float(np.corrcoef(centrality_values, impacts)[0, 1])
    return centrality_values, impacts, corr


def plot_survival_curves(curves: dict[str, np.ndarray], out_path: Path) -> None:
    plt.figure(figsize=(7, 5))
    for strategy, curve in curves.items():
        plt.plot(curve * 100, label=strategy, marker="o", markersize=3)
    plt.axhline(50, linestyle="--", color="gray", label="50% saturation")
    plt.xlabel("timestep")
    plt.ylabel("nodes still alive (%)")
    plt.title("network survival under DDoS-style cascade, by mitigation strategy")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def plot_centrality_vs_impact(
    centrality_values: list[float], impacts: list[float], correlation: float, out_path: Path
) -> None:
    plt.figure(figsize=(6, 5))
    plt.scatter(centrality_values, impacts, alpha=0.7)
    plt.xlabel("betweenness centrality")
    plt.ylabel("mean nodes failed when this node fails first")
    plt.title(f"centrality vs. cascade impact (Pearson r = {correlation:.3f})")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
