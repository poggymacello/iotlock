# Data

## Real data: Internet Topology Zoo

276 real telecommunications network topologies (nodes = routers/PoPs,
edges = physical links), transcribed from public operator maps.

- **Source**: the original site, `topology-zoo.org`, has gone offline
  (verified with a direct HTTP request before writing
  `scripts/download_data.py` -- it returns no response at all). This
  project instead fetches the GraphML archive from
  [`mroughan/InternetTopologyZoo`](https://github.com/mroughan/InternetTopologyZoo),
  an actively-maintained long-term mirror run by one of the original
  paper's co-authors (Matthew Roughan) specifically because the primary
  site was expected to lose support.
- **License / citation**: cite Knight, S., Nguyen, H.X., Falkner, N.,
  Bowden, R., and Roughan, M. "The Internet Topology Zoo." IEEE Journal
  on Selected Areas in Communications, vol. 29, no. 9, pp. 1765-1775,
  October 2011.
- **SHA256** of `graphml.tar.gz` (pinned in `scripts/download_data.py`):
  `7fba0617df71911a30df116478d1fc75758963c7b2569dd81818f47cf5b814c1`
- **Access date**: 2026-07-24.
- Not committed to git in full (502KB archive, ~276 files). Fetch with
  `python scripts/download_data.py`.

### Filtering

Real topologies range from a handful of nodes to 750+ (the largest
backbone networks). `topology_real.load_topologies` keeps only
connected graphs with 15-150 nodes (large enough to have real
structure, small enough to run hundreds of Monte Carlo trials across
hundreds of topologies quickly) -- 210 of the 276 topologies pass this
filter and are used for every Results number in the README.

## Real data: N-BaIoT

Real network traffic from 9 commercial IoT devices, each infected in a
lab by real Mirai and/or BASHLITE (gafgyt) malware (Meidan et al.,
2018). This project uses **3 of the 9 devices** (a doorbell, a
thermostat, a security camera) and **one attack subtype per botnet
family** (`scan`) -- see "Why only a subset" below.

- **Source**: UCI Machine Learning Repository,
  `archive.ics.uci.edu/dataset/442`.
- **License / citation**: cite Meidan, Y., Bohadana, M., Mathov, Y.,
  Mirsky, Y., Breitenbacher, D., Shabtai, A., and Elovici, Y.
  "N-BaIoT: Network-Based Detection of IoT Botnet Attacks Using Deep
  Autoencoders." IEEE Pervasive Computing, 2018.
- **SHA256** of the full source zip (pinned in `scripts/download_data.py`):
  `64929678b081d8e579a8d7c488cf11cc588403f282d5fb065b4156edbd55de9b`
- **Access date**: 2026-07-23.
- Not committed to git (~370MB for the 3-device subset used here).
  Fetch with `python scripts/download_data.py` (requires 7-Zip's `7z`
  command on PATH to extract the RAR-compressed attack files -- see
  below).

### Why only a subset

The full dataset (9 devices x benign + 2 botnet families x 5 attack
subtypes each) is ~2.1GB uncompressed and RAR-compressed. This project
uses 3 devices spanning different device types, plus one attack
subtype (`scan`) per botnet family -- chosen because it's present and
comparably sized across all 3 devices -- rather than all 45 device x
attack-subtype combinations. This keeps the download and the detection
pipeline tractable while remaining genuinely real N-BaIoT traffic, not
a synthetic stand-in. `scan` traffic also turns out to be an easy attack
type to detect (see README's Leakage Controls); other subtypes (e.g.,
low-rate UDP floods) were not evaluated and may show messier
separation from benign traffic.

### RAR extraction requirement

N-BaIoT's per-attack-family files (`gafgyt_attacks.rar`,
`mirai_attacks.rar`) are RAR archives. `scripts/download_data.py` shells
out to a `7z` command (7-Zip, or any RAR-capable extractor providing
the same command name) to extract just the `scan.csv` entry from each
-- Python's standard library has no RAR support. Install 7-Zip and
ensure `7z` is on PATH before running the download script.

Each device's raw features are 115-dimensional statistical summaries of
network traffic (packet rate/size statistics over several decay
windows), extracted by N-BaIoT's own published pipeline -- there is no
raw packet capture or payload data anywhere in this project.

## Sample fixtures

`data/sample/topology_zoo/` (15 small real topologies, ~250KB) and
`data/sample/nbaiot/` (150-row-per-class subsamples for the 3 devices
used, ~1.6MB) are small, committed fixtures used by CI and the test
suite. Neither is used for any reported README result -- those come
from the full filtered topology set (210 graphs) and the full 3-device
N-BaIoT subset via `python -m iotlock real-train`.

## Synthetic fallback (v1)

The original synthetic Barabási-Albert topology generator
(`src/iotlock/topology.py`) and traffic/cascade simulator
(`src/iotlock/simulation.py`) are still present and still exercised by
the `train`/`eval` CLI commands and their tests, kept as a fast,
dependency-free smoke test of the mitigation-strategy comparison
independent of real data. See the README's "What changed from v1"
section.
