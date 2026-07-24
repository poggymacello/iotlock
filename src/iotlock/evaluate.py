"""Monte Carlo evaluation of mitigation strategies and a centrality-vs-impact check."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from iotlock.simulation import simulate_cascade


@dataclass
class DetectionMetrics:
    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float

    def as_dict(self) -> dict[str, float]:
        return {
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "roc_auc": round(self.roc_auc, 4),
            "pr_auc": round(self.pr_auc, 4),
        }


def compute_detection_metrics(
    y_true, scores: np.ndarray, threshold: float = 0.5
) -> DetectionMetrics:
    y_pred = (scores >= threshold).astype(int)
    return DetectionMetrics(
        precision=precision_score(y_true, y_pred, zero_division=0),
        recall=recall_score(y_true, y_pred, zero_division=0),
        f1=f1_score(y_true, y_pred, zero_division=0),
        roc_auc=roc_auc_score(y_true, scores),
        pr_auc=average_precision_score(y_true, scores),
    )


def recall_at_fpr(y_true, scores: np.ndarray, max_fpr: float) -> float:
    fpr, tpr, _ = roc_curve(y_true, scores)
    valid = fpr <= max_fpr
    if not valid.any():
        return 0.0
    return float(tpr[valid].max())


def polarity_warning(roc_auc: float) -> str | None:
    if roc_auc < 0.4:
        return (
            f"ROC-AUC={roc_auc:.4f} is well below 0.5 -- check for an inverted "
            f"label or score polarity before concluding the model is just weak "
            f"(1 - {roc_auc:.4f} = {1 - roc_auc:.4f})"
        )
    return None


def bootstrap_ci(
    y_true, scores: np.ndarray, n_bootstrap: int = 1000, seed: int = 42, confidence: float = 0.95
) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    scores = np.asarray(scores)
    n = len(y_true)

    point_estimate = float(average_precision_score(y_true, scores))
    samples = []
    for _ in range(n_bootstrap):
        idx = rng.integers(0, n, n)
        y_sample = y_true[idx]
        if y_sample.min() == y_sample.max():
            continue
        samples.append(average_precision_score(y_sample, scores[idx]))

    alpha = (1 - confidence) / 2
    return {
        "point_estimate": round(point_estimate, 4),
        "ci_lower": round(float(np.quantile(samples, alpha)), 4),
        "ci_upper": round(float(np.quantile(samples, 1 - alpha)), 4),
    }


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


def plot_correlation_distribution(correlations: list[float], out_path: Path) -> None:
    """Histogram of the per-topology centrality-impact Pearson correlation,
    across many real topologies -- the real-data analog of
    ``plot_centrality_vs_impact``'s single-topology scatter plot, since a
    single scatter plot doesn't generalize to "many topologies at once"
    the way a distribution of their correlations does.
    """
    arr = np.array(correlations)
    plt.figure(figsize=(6, 5))
    plt.hist(arr, bins=20, color="#2563eb", alpha=0.8)
    plt.axvline(float(np.median(arr)), linestyle="--", color="gray", label="median")
    plt.xlabel("per-topology Pearson r (centrality vs. cascade impact)")
    plt.ylabel("number of topologies")
    plt.title(f"centrality-impact correlation across {len(arr)} real topologies")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
