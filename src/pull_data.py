"""Freeze raw data. The only script in this project that touches the network.

Pulls:
  - FBS schedules with scores and pregame Elo from sportsdataverse/cfbfastR-data
    (schedules/parquet/cfb_schedules_YYYY.parquet), via a sparse, blobless clone.
  - Weekly polls from the CollegeFootballData.com API (/rankings), regular season
    and postseason, saved exactly as returned.

Writes data/MANIFEST.json with source URL, pull time, and SHA-256 for every file,
plus the upstream commit hash of cfbfastR-data.

Needs CFBD_API_KEY in the environment. The key is never printed or written to disk.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CLONE = RAW / "cfbfastR-data"
SCHED_DIR = RAW / "schedules"
POLL_DIR = RAW / "polls"
MANIFEST = ROOT / "data" / "MANIFEST.json"

SEASONS = range(2014, 2027)
SDV_REPO = "https://github.com/sportsdataverse/cfbfastR-data"
CFBD_BASE = "https://api.collegefootballdata.com"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, cwd=None):
    env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1")
    return subprocess.run(cmd, cwd=cwd, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


def pull_schedules():
    if CLONE.exists():
        shutil.rmtree(CLONE)
    run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
         SDV_REPO, str(CLONE)])
    run(["git", "sparse-checkout", "set", "schedules/parquet"], cwd=CLONE)
    commit = run(["git", "rev-parse", "HEAD"], cwd=CLONE)

    SCHED_DIR.mkdir(parents=True, exist_ok=True)
    files = {}
    for season in SEASONS:
        name = f"cfb_schedules_{season}.parquet"
        src = CLONE / "schedules" / "parquet" / name
        if not src.exists():
            sys.exit(f"Missing upstream file: schedules/parquet/{name}")
        with open(src, "rb") as f:
            if f.read(4) != b"PAR1":
                sys.exit(f"{name} is not a parquet file (Git LFS pointer?)")
        dst = SCHED_DIR / name
        shutil.copyfile(src, dst)
        files[str(dst.relative_to(ROOT))] = {
            "source_url": f"{SDV_REPO}/blob/{commit}/schedules/parquet/{name}",
            "sha256": sha256(dst),
            "bytes": dst.stat().st_size,
        }
    return commit, files


def cfbd_get(path):
    key = os.environ.get("CFBD_API_KEY")
    if not key:
        sys.exit("CFBD_API_KEY is not set")
    req = urllib.request.Request(CFBD_BASE + path, headers={
        "Authorization": f"Bearer {key}", "Accept": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception as e:
            if attempt == 3:
                sys.exit(f"CFBD request failed for {path}: {type(e).__name__}")
            time.sleep(2 ** (attempt + 1))


def pull_polls():
    POLL_DIR.mkdir(parents=True, exist_ok=True)
    files = {}
    for season in SEASONS:
        for season_type in ("regular", "postseason"):
            path = f"/rankings?year={season}&seasonType={season_type}"
            body = cfbd_get(path)
            json.loads(body)  # fail loudly on anything that isn't JSON
            dst = POLL_DIR / f"rankings_{season}_{season_type}.json"
            dst.write_bytes(body)
            files[str(dst.relative_to(ROOT))] = {
                "source_url": CFBD_BASE + path,
                "sha256": sha256(dst),
                "bytes": dst.stat().st_size,
            }
    return files


def main():
    pulled_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    commit, sched_files = pull_schedules()
    poll_files = pull_polls()
    manifest = {
        "pulled_at_utc": pulled_at,
        "sources": {
            "cfbfastR-data": {"repo": SDV_REPO, "commit": commit},
            "cfbd": {"base_url": CFBD_BASE, "endpoint": "/rankings"},
        },
        "files": dict(sorted({**sched_files, **poll_files}.items())),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Froze {len(manifest['files'])} files; cfbfastR-data @ {commit}")


if __name__ == "__main__":
    main()
