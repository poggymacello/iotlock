# Model Card: IoTLock

## Purpose

Two components:

- **Mitigation simulation** (no trained model): Monte Carlo comparison
  of three defensive strategies (none, rate limiting, automatic
  isolation) against a cascading-failure model, run across real network
  topologies from the Internet Topology Zoo, plus a centrality-vs-impact
  correlation check. Pure simulation -- never touches a real network.
- **Botnet detector** (trained, deployed at `/predict`): a gradient
  boosting classifier over 115 real N-BaIoT static traffic features,
  evaluated with a device-holdout split (trained on 2 of 3 devices,
  tested on a device type never seen during training).

v1 ran the mitigation simulation on one synthetic Barabási-Albert graph
and had no detection component at all. See README's "What changed from
v1."

## Data

- Internet Topology Zoo: 210 real, connected network topologies
  (15-150 nodes each), from a public mirror of the original dataset.
- N-BaIoT: real traffic from 3 real IoT devices, each infected in a lab
  by real Mirai and BASHLITE malware, plus their own pre-infection
  benign traffic.

See [`data/README.md`](data/README.md) for full source, license,
citation, and subsetting rationale.

## Metrics

**Mitigation** (across 210 real topologies, `python -m iotlock real-train`):
final survival % distribution -- rate_limit median 99.67% (p10 98.75,
p90 100.0), isolate_failed median 59.64% (p10 58.13, p90 61.62), none
median 18.42% (p10 6.84, p90 29.19). Centrality-impact correlation
across the same 210 topologies: median r=0.69 (p10 0.24, p90 0.94),
down from v1's single-topology r=0.966.

**Detection** (device-holdout test split): ROC-AUC 1.000, PR-AUC 1.000,
recall@1%FPR 1.000. See README's Leakage Controls for why this
near-perfect score is investigated and resolved as a real characteristic
of the specific attack type used (`scan` floods), not leakage --
17 of 115 individual features already exceed the 0.98 suspicious-AUC
threshold, consistent with how statistically distinct scan-flood traffic
is from normal IoT device traffic.

## Limitations

- The detector was evaluated on one attack subtype (`scan`) per botnet
  family; other subtypes (e.g., low-rate UDP floods) were not evaluated
  and may show messier separation from benign traffic -- the reported
  near-perfect metrics should not be read as "this detects all botnet
  traffic," only "this detects scan-flood traffic from devices/families
  like these."
- The mitigation model's traffic/capacity assumptions (fixed capacity,
  Poisson load, 50%-of-neighbors cascade rule) remain a simplification
  chosen for legibility, not a validated model of real network
  congestion -- now applied to real topologies, but still a simulated
  traffic model, not real traffic.
- Only 3 of N-BaIoT's 9 devices were used; generalization to the other
  6 device types (and to Mirai/BASHLITE variants not represented here)
  is untested.

## Not recommended for

Any real network security decision. Both components are portfolio
methodology demonstrations: the mitigation simulation never touches a
real network, and the detector's near-perfect metrics reflect a
best-case attack scenario (see Limitations), not validated production
detection performance.
