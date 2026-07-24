"""Monte Carlo mitigation comparison across MANY real topologies, and a
centrality-impact correlation revalidated per-topology rather than on a
single synthetic graph.

v1 ran this on one synthetic Barabási-Albert graph and reported single
numbers (99.6% survival under rate limiting, Pearson r=0.966). Doing the
same thing across ~200 real, structurally diverse topologies (rather
than one graph, however realistic its degree distribution) means the
result is a *distribution* of outcomes, not a single number that could
just be an artifact of one specific graph's structure -- which is also
why the reported result here is percentiles, not a mean pretending to
represent every network equally well.
"""

from __future__ import annotations

import networkx as nx
import numpy as np

from iotlock import evaluate as eval_mod
from iotlock.simulation import STRATEGIES
from iotlock.topology import compute_centrality
from iotlock.topology_real import load_topologies


def run_mitigation_across_topologies(
    topologies: list[tuple[str, nx.Graph]] | None = None,
    n_trials: int = 20,
    max_timesteps: int = 20,
    seed: int = 42,
) -> dict:
    graphs = topologies if topologies is not None else load_topologies()

    per_strategy_final_survival: dict[str, list[float]] = {s: [] for s in STRATEGIES}
    per_strategy_time_to_saturation: dict[str, list[int | None]] = {s: [] for s in STRATEGIES}

    for _name, graph in graphs:
        for strategy in STRATEGIES:
            curve = eval_mod.survival_curve(
                graph, strategy, n_trials=n_trials, max_timesteps=max_timesteps, seed=seed
            )
            per_strategy_final_survival[strategy].append(float(curve[-1] * 100))
            per_strategy_time_to_saturation[strategy].append(
                eval_mod.time_to_saturation(curve, threshold=0.5)
            )

    survival_distribution = {
        strategy: _percentile_summary(values)
        for strategy, values in per_strategy_final_survival.items()
    }

    return {
        "n_topologies": len(graphs),
        "survival_distribution_pct": survival_distribution,
        "raw_final_survival_pct": per_strategy_final_survival,
        "time_to_saturation": per_strategy_time_to_saturation,
    }


def run_centrality_impact_across_topologies(
    topologies: list[tuple[str, nx.Graph]] | None = None,
    n_trials: int = 4,
    max_timesteps: int = 10,
    seed: int = 42,
) -> dict:
    graphs = topologies if topologies is not None else load_topologies()

    correlations = []
    per_topology = {}
    for name, graph in graphs:
        centrality = compute_centrality(graph)
        _, _, corr = eval_mod.centrality_vs_impact(
            graph, centrality, n_trials=n_trials, max_timesteps=max_timesteps, seed=seed
        )
        if not np.isnan(corr):
            correlations.append(corr)
            per_topology[name] = round(corr, 4)

    return {
        "n_topologies_with_valid_correlation": len(correlations),
        "correlation_distribution": _percentile_summary(correlations),
        "per_topology_correlation": per_topology,
    }


def _percentile_summary(values: list[float]) -> dict[str, float]:
    arr = np.array([v for v in values if v is not None], dtype=float)
    if len(arr) == 0:
        return {"p10": None, "p25": None, "p50": None, "p75": None, "p90": None, "mean": None}
    return {
        "p10": round(float(np.percentile(arr, 10)), 2),
        "p25": round(float(np.percentile(arr, 25)), 2),
        "p50": round(float(np.percentile(arr, 50)), 2),
        "p75": round(float(np.percentile(arr, 75)), 2),
        "p90": round(float(np.percentile(arr, 90)), 2),
        "mean": round(float(arr.mean()), 2),
    }
