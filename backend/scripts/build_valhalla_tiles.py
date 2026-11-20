"""Build the Valhalla tile set for the walking engine (Phase 3, ADR-0008).

Runs the three Valhalla build stages inside the pinned container image
(`ghcr.io/valhalla/valhalla:3.5.1`; `latest` segfaults on this host — I-22):

  1. `valhalla_build_config` — writes data/osm/valhalla_config.json (UTF-8;
     never redirect Docker output through PowerShell, which writes UTF-16).
  2. `valhalla_build_tiles` — builds loose tiles from the OSM pbf.
  3. `valhalla_build_extract` — packs tiles.tar that `valhalla_service` loads.

Usage (repository root):
    python backend/scripts/build_valhalla_tiles.py [data/osm/sri-lanka-261119.osm.pbf]

Output stays under data/osm (gitignored). The build took ~9 minutes for the
full Sri Lanka extract on this machine; tiles.tar is ~126 MB.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

IMAGE = "ghcr.io/valhalla/valhalla:3.5.1"
DEFAULT_PBF = "data/osm/sri-lanka-261119.osm.pbf"
TILE_DIR = "/data/valhalla-tiles"

REPO_ROOT = Path(__file__).resolve().parents[2]
OSM_DIR = REPO_ROOT / "data" / "osm"
CONFIG_PATH = OSM_DIR / "valhalla_config.json"
TILES_PATH = OSM_DIR / "valhalla-tiles"


def run(args: list[str], label: str) -> str:
    print(f"==> {label}", flush=True)
    started = time.perf_counter()
    result = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.perf_counter() - started
    if result.returncode != 0:
        print(result.stdout)
        raise SystemExit(f"{label} failed with exit code {result.returncode}")
    print(f"    done in {elapsed:.0f}s")
    return result.stdout


def main() -> None:
    pbf = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / DEFAULT_PBF
    if not pbf.is_file():
        raise SystemExit(f"OSM pbf not found: {pbf}")
    osm_volume = pbf.parent.resolve()
    pbf_in_container = f"/data/{pbf.name}"
    config_in_container = f"/data/{CONFIG_PATH.name}"

    config = run(
        [
            "docker",
            "run",
            "--rm",
            IMAGE,
            "valhalla_build_config",
            f"--mjolnir-tile-dir={TILE_DIR}",
            "--mjolnir-concurrency=4",
            "--mjolnir-id=0",
        ],
        "stage 1/3: valhalla_build_config",
    )
    CONFIG_PATH.write_text(config, encoding="utf-8")
    print(f"    wrote {CONFIG_PATH.relative_to(REPO_ROOT)} ({len(config)} bytes)")

    if TILES_PATH.exists():
        shutil.rmtree(TILES_PATH)
    run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{osm_volume}:/data",
            IMAGE,
            "valhalla_build_tiles",
            "-c",
            config_in_container,
            pbf_in_container,
        ],
        "stage 2/3: valhalla_build_tiles",
    )

    run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{osm_volume}:/data",
            IMAGE,
            "valhalla_build_extract",
            "-c",
            config_in_container,
        ],
        "stage 3/3: valhalla_build_extract",
    )

    extract = OSM_DIR / "valhalla" / "tiles.tar"
    if extract.is_file():
        print(
            f"tiles.tar ready: {extract.relative_to(REPO_ROOT)} "
            f"({extract.stat().st_size / (1024 * 1024):.1f} MB)"
        )
    print("Start the service with: docker compose -f infra/docker/compose.yaml up -d valhalla")


if __name__ == "__main__":
    main()
