# Security Policy

This is a personal research/portfolio project, not a maintained production
system, but reports are still welcome.

## Reporting a vulnerability

If you find a security issue in this repository (in the detection code,
the API service, the Docker image, or a dependency this project pins to a
version with a known vulnerability that hasn't been updated yet), please
open a GitHub issue on this repository with:

- A description of the issue and where it is (file/endpoint/dependency)
- Steps to reproduce, if applicable
- Why you believe it's a security issue rather than a regular bug

There is no bug bounty and no formal SLA -- this is maintained by one
person in their spare time -- but reports will be read and, if valid,
addressed.

## Scope

In scope: the API service (`src/iotlock/api.py`), the model
artifact/loading code, the Dockerfile, and this repository's pinned
dependencies.

Out of scope: the Internet Topology Zoo and N-BaIoT datasets themselves
(report data issues to their respective maintainers), and anything
about how you've deployed this project outside of what's documented
here.

## What this project already does defensively

This project remains pure defensive simulation and detection throughout.
`/simulate` runs a cascade model against a real network's *topology*
only (nodes and links, no live traffic, no real infrastructure
contacted) -- it cannot be used to flood, probe, or otherwise affect any
real network. `/simulate`'s topology name is validated against a fixed,
preloaded allowlist (the graphs this service loaded at startup), so it
cannot be used to make the server read an arbitrary file path. `/predict`
scores a caller-supplied numeric feature vector; it never fetches,
stores, or executes anything. Beyond that: rate limiting, no detection
feature values ever logged, a non-root container user, and CI checks
(`pip-audit`, `bandit`) on every push.
