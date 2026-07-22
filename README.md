# IoTLock

Simulation and visualization of DDoS attack patterns over an IoT network topology.

## Overview

IoT deployments tend to be flat, densely interconnected networks where a handful of nodes end up carrying most of the traffic between everything else. That structure makes them an interesting case for thinking about how a denial-of-service attack propagates: does failure stay isolated, or does it cascade through the nodes that hold the network together? This project builds a random IoT-like graph, reduces it to a minimum spanning tree to expose the backbone connections, then simulates an escalating flood of traffic across that backbone and animates the result.

This is a simulation and visualization tool for understanding attack propagation patterns, not an attack tool. Everything here runs against a randomly generated, synthetic graph.

## Method

The network is built as a random graph over 20 nodes, with each pair of nodes connected with 30% probability and a random weight (1 to 10) standing in for link latency. `networkx` computes the minimum spanning tree over this graph via Kruskal's algorithm, giving a backbone of essential connections.

Attack traffic is then simulated per timestep against that backbone:

- each node's incoming packet count is drawn from a Poisson distribution whose rate increases with time, modeling an escalating flood
- a node fails once it receives more than 15 packets, or once at least half of its neighbors have already failed, capturing a simple cascading-failure effect
- betweenness centrality on the spanning tree is combined with each node's failure count to score which nodes had the most structural impact when they went down

The per-timestep node states are rendered frame by frame with `matplotlib` and exported as an animated GIF via the Pillow writer, matplotlib running headless on the `Agg` backend.

## Results

![DDoS simulation](assets/simulasi_ddos.gif)

The animation shows the backbone topology with nodes colored green (normal) or red (failed), a title block reporting the failure percentage and average link latency at each timestep, and a progress bar tracking the simulation. As the attack intensity ramps up over time, failures start at individual nodes and spread outward through their neighbors, and the nodes identified by the impact score tend to be the ones whose failure disconnects the largest parts of the tree.

## Getting started

```bash
git clone https://github.com/poggymacello/iotlock.git
cd iotlock
python3 -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 src/iotlock.py
```

Running the script builds the network, runs the simulation, prints the nodes with the highest impact scores, and writes the animation to `assets/simulasi_ddos.gif`.

## Project structure

```
iotlock/
├── src/iotlock.py          # graph construction, MST, simulation, animation
├── assets/                  # generated output (DDoS simulation GIF)
├── requirements.txt
├── LICENSE
└── README.md
```

## License

MIT, see [LICENSE](LICENSE).
