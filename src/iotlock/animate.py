"""Animated visualization of a single baseline (no-mitigation) cascade run."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import Patch


def animate_cascade(graph: nx.Graph, history: list[dict[int, bool]]) -> animation.FuncAnimation:
    fig = plt.figure(figsize=(12, 9))
    gs = fig.add_gridspec(2, 1, height_ratios=[6, 1], hspace=0.3)
    ax_graph = fig.add_subplot(gs[0])
    ax_progress = fig.add_subplot(gs[1])

    plt.style.use("ggplot")
    pos = nx.spring_layout(graph, k=1, iterations=50, seed=42)
    total_nodes = graph.number_of_nodes()

    def update(frame: int) -> None:
        ax_graph.clear()
        ax_progress.clear()

        state = history[frame]
        failed_nodes = sum(state.values())
        percent_failed = (failed_nodes / total_nodes) * 100

        node_colors = ["#ff4444" if state[n] else "#44ff44" for n in graph.nodes()]
        node_sizes = [400 if state[n] else 200 for n in graph.nodes()]

        ax_graph.grid(True, linestyle="--", alpha=0.5)
        nx.draw_networkx_edges(graph, pos, edge_color="gray", alpha=0.3, ax=ax_graph)
        nx.draw_networkx_nodes(
            graph, pos, node_color=node_colors, node_size=node_sizes, ax=ax_graph
        )

        legend_elements = [
            Patch(facecolor="#44ff44", label="node normal"),
            Patch(facecolor="#ff4444", label="node gagal"),
        ]
        ax_graph.legend(handles=legend_elements, loc="upper right")
        ax_graph.set_title(
            "IoT topology under a DDoS-style cascade (no mitigation)\n"
            f"timestep {frame}: {failed_nodes}/{total_nodes} nodes failed ({percent_failed:.1f}%)"
        )

        progress = (frame + 1) / len(history)
        ax_progress.barh(0, progress * 100, color="#2196f3", alpha=0.8)
        ax_progress.barh(0, 100, color="gray", alpha=0.2)
        ax_progress.set_xlim(0, 100)
        ax_progress.set_ylim(-0.5, 0.5)
        ax_progress.set_xlabel(f"progress: {progress * 100:.0f}%")
        ax_progress.set_yticks([])

    return animation.FuncAnimation(
        fig, update, frames=len(history), interval=500, repeat=True, cache_frame_data=False
    )
