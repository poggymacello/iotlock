"""Cascading traffic-overload simulation with defensive mitigation strategies.

Node capacity is fixed; incoming traffic escalates over time (Poisson,
increasing intensity) to model a ramping DDoS-style flood. A node fails if
its traffic exceeds capacity, or if enough of its neighbors have already
failed (a cascading effect: losing half your neighbors typically means
losing the paths that were carrying your traffic too).

Three strategies are compared, purely as a simulation of defensive
response, not an attack tool:

- ``"none"``: no mitigation, the raw cascade.
- ``"rate_limit"``: incoming traffic is throttled by a fixed fraction
  before the overload check, a simple defensive rate limiter. This lowers
  the probability of direct overload without eliminating it (a large
  enough flood still gets through) and does nothing about the
  neighbor-cascade effect.
- ``"isolate_failed"``: failed nodes are removed from the graph entirely
  for the purposes of computing later cascade pressure, modeling automatic
  quarantine/rerouting around a known-bad node. This removes the
  neighbor-cascade effect altogether, leaving only direct overload as a
  failure cause, so it isolates how much of the damage in "none" was
  actually caused by cascading versus raw overload.

Traffic intensity is deliberately kept bounded rather than escalating
without limit: with ``max_timesteps`` independent per-node overload draws,
any strategy converges to near-total failure eventually if the per-step
overload probability is too high, which would make every strategy look
identical over a long enough run. A bounded, modest overload probability
per step is what lets the cascade mechanism (rather than raw overload
alone) be the dominant driver of collapse under "none", and lets the
mitigation strategies show a real, distinguishable difference within the
simulated horizon.
"""

from __future__ import annotations

import networkx as nx
import numpy as np

STRATEGIES = ("none", "rate_limit", "isolate_failed")


def simulate_cascade(
    graph: nx.Graph,
    strategy: str = "none",
    max_timesteps: int = 20,
    capacity: int = 15,
    rate_limit_factor: float = 0.7,
    seed: int = 42,
    start_node: int | None = None,
) -> list[dict[int, bool]]:
    """Returns a list of {node: failed} snapshots, one per timestep (including t=0)."""
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}, expected one of {STRATEGIES}")

    rng = np.random.default_rng(seed)
    nodes = list(graph.nodes())
    original_degree = dict(graph.degree())
    failed = dict.fromkeys(nodes, False)
    if start_node is not None:
        failed[start_node] = True

    history: list[dict[int, bool]] = [dict(failed)]

    for t in range(max_timesteps):
        new_failed = dict(failed)
        for node in nodes:
            if failed[node]:
                continue

            lam = min(6 + 0.3 * t, 10.0)  # bounded escalation, see module docstring
            traffic = rng.poisson(lam)
            if strategy == "rate_limit":
                traffic = int(traffic * rate_limit_factor)
            overloaded = traffic > capacity

            if strategy == "isolate_failed":
                # failed neighbors are treated as removed from the graph
                # (rerouted around), so there is no cascade pressure left
                # to compute here; only direct overload remains
                cascades = False
            else:
                neighbors = list(graph.neighbors(node))
                failed_neighbors = sum(1 for nb in neighbors if failed[nb])
                denom = original_degree[node] if original_degree[node] > 0 else 1
                cascades = failed_neighbors >= denom / 2

            new_failed[node] = overloaded or cascades

        failed = new_failed
        history.append(dict(failed))

    return history
