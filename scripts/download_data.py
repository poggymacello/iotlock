"""Download real Internet Topology Zoo topologies and a real N-BaIoT
botnet traffic subset.

**Internet Topology Zoo**: the original topology-zoo.org site has gone
offline (verified before writing this script -- see data/README.md).
Downloads the GraphML archive from the actively-maintained long-term
mirror, `mroughan/InternetTopologyZoo` on GitHub, instead.

**N-BaIoT**: the full dataset (9 devices x benign + 2 botnet families x
5 attack subtypes each) is ~2.1GB, RAR-compressed. This project uses 3
devices' benign traffic plus one attack subtype (`scan`) from each
botnet family (~370MB) -- see data/README.md for why. Extracting the
RAR archives requires 7-Zip (or another `rar`-capable extractor) on
PATH; this script shells out to `7z`.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

TOPOLOGY_ZOO_URL = "https://raw.githubusercontent.com/mroughan/InternetTopologyZoo/main/graphml.tar.gz"
TOPOLOGY_ZOO_SHA256 = "7fba0617df71911a30df116478d1fc75758963c7b2569dd81818f47cf5b814c1"

NBAIOT_URL = (
    "https://archive.ics.uci.edu/static/public/442/"
    "detection+of+iot+botnet+attacks+n+baiot.zip"
)
NBAIOT_ZIP_SHA256 = "64929678b081d8e579a8d7c488cf11cc588403f282d5fb065b4156edbd55de9b"
NBAIOT_DEVICES = (
    "Danmini_Doorbell",
    "Ecobee_Thermostat",
    "SimpleHome_XCS7_1003_WHT_Security_Camera",
)


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fail(message: str) -> None:
    print(f"FATAL: {message}", file=sys.stderr)
    sys.exit(1)


def download_topology_zoo() -> None:
    topo_dir = DATA_DIR / "topology_zoo"
    if topo_dir.exists() and any(topo_dir.glob("*.graphml")):
        print("topology_zoo/: already present, skipping")
        return

    archive = DATA_DIR / "graphml.tar.gz"
    print(f"downloading {TOPOLOGY_ZOO_URL}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(TOPOLOGY_ZOO_URL, archive)  # noqa: S310 (checksum-verified below)

    actual = _sha256_of(archive)
    if actual != TOPOLOGY_ZOO_SHA256:
        archive.unlink()
        _fail(
            f"graphml.tar.gz checksum mismatch (expected {TOPOLOGY_ZOO_SHA256}, got {actual}). "
            "Not proceeding with unverified data -- see data/README.md."
        )

    with tarfile.open(archive) as tf:
        tf.extractall(DATA_DIR)  # noqa: S202 (trusted, checksum-verified archive)
    archive.unlink()
    (DATA_DIR / "graphml").rename(topo_dir)  # the tarball's top-level dir is "graphml/"

    n_graphs = len(list(topo_dir.glob("*.graphml")))
    print(f"topology_zoo/: extracted and verified ({n_graphs} graphml files)")


def download_nbaiot() -> None:
    nbaiot_dir = DATA_DIR / "nbaiot"
    expected_files = [
        nbaiot_dir / device / name
        for device in NBAIOT_DEVICES
        for name in ("benign_traffic.csv", "gafgyt_scan.csv", "mirai_scan.csv")
    ]
    if all(p.exists() for p in expected_files):
        print("nbaiot/: already present, skipping")
        return

    zip_path = DATA_DIR / "nbaiot_full.zip"
    if not (zip_path.exists() and _sha256_of(zip_path) == NBAIOT_ZIP_SHA256):
        print(f"downloading {NBAIOT_URL} (~1.7GB, this takes a while)")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(NBAIOT_URL, zip_path)  # noqa: S310 (checksum-verified below)

        actual = _sha256_of(zip_path)
        if actual != NBAIOT_ZIP_SHA256:
            zip_path.unlink()
            _fail(
                f"nbaiot_full.zip checksum mismatch (expected {NBAIOT_ZIP_SHA256}, got {actual}). "
                "Not proceeding with unverified data -- see data/README.md."
            )

    import zipfile

    with zipfile.ZipFile(zip_path) as zf:
        for device in NBAIOT_DEVICES:
            zf.extract(f"{device}/benign_traffic.csv", DATA_DIR)

    for device in NBAIOT_DEVICES:
        dest_dir = nbaiot_dir / device
        dest_dir.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / device / "benign_traffic.csv").rename(dest_dir / "benign_traffic.csv")

        for _family, rar_name, out_name in [
            ("gafgyt", "gafgyt_attacks.rar", "gafgyt_scan.csv"),
            ("mirai", "mirai_attacks.rar", "mirai_scan.csv"),
        ]:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extract(f"{device}/{rar_name}", DATA_DIR)
            rar_path = DATA_DIR / device / rar_name
            try:
                subprocess.run(  # noqa: S603 (fixed args, no shell, trusted local file)
                    ["7z", "e", str(rar_path), f"-o{dest_dir}", "scan.csv", "-y"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except FileNotFoundError:
                _fail(
                    "the '7z' command was not found on PATH. Extracting N-BaIoT's "
                    "RAR-compressed attack files requires 7-Zip (or another "
                    "rar-capable extractor providing a `7z` command). Install it "
                    "and retry."
                )
            (dest_dir / "scan.csv").rename(dest_dir / out_name)
            rar_path.unlink()
        (DATA_DIR / device).rmdir()

    print(f"nbaiot/: extracted {len(NBAIOT_DEVICES)} devices (benign + gafgyt/mirai scan traffic)")
    zip_path.unlink()


def main() -> None:
    download_topology_zoo()
    download_nbaiot()
    print(f"\nall data verified in {DATA_DIR}/")


if __name__ == "__main__":
    main()
