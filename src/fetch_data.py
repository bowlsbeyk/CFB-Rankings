"""Download the frozen raw data and verify it against data/MANIFEST.json.

The raw files are not committed (CollegeFootballData.com terms; DEVIATIONS.md,
2026-10-23). This script rebuilds them byte for byte:
  - schedules from sportsdataverse/cfbfastR-data at each file's pinned commit (no key)
  - polls from the CFBD API (free key in CFBD_API_KEY); a season still in progress
    is cut back to the poll weeks that were frozen ("frozen_through_week") before checking

Files already present with the right checksum are left alone, so this needs the
network (and the key) only for files that are missing. Any mismatch is an error.
Unlike pull_data.py, it never changes the manifest.
"""

import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "MANIFEST.json"
SCHEDULE_RAW = "https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/{commit}/schedules/parquet/{name}"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception as e:
            if attempt == 3:
                sys.exit(f"Download failed for {url.split('?')[0]}: {type(e).__name__}")
            time.sleep(2 ** (attempt + 1))


def fetch_schedule(rel, meta):
    commit = meta["source_url"].split("/blob/")[1].split("/")[0]
    return get(SCHEDULE_RAW.format(commit=commit, name=Path(rel).name))


def fetch_poll(rel, meta):
    key = os.environ.get("CFBD_API_KEY")
    if not key:
        sys.exit(f"{rel} is missing and CFBD_API_KEY is not set. Get a free key at "
                 "https://collegefootballdata.com/key and export it, then re-run.")
    body = get(meta["source_url"], {"Authorization": f"Bearer {key}", "Accept": "application/json"})
    cut = meta.get("frozen_through_week")
    if cut is not None:
        weeks = [w for w in json.loads(body) if w["week"] <= cut]
        body = json.dumps(weeks, separators=(",", ":"), ensure_ascii=False).encode()
    return body


def main():
    manifest = json.loads(MANIFEST.read_text())
    fetched = kept = 0
    for rel, meta in manifest["files"].items():
        path = ROOT / rel
        if path.exists() and sha256(path.read_bytes()) == meta["sha256"]:
            kept += 1
            continue
        body = fetch_schedule(rel, meta) if "/schedules/" in rel else fetch_poll(rel, meta)
        if sha256(body) != meta["sha256"]:
            sys.exit(f"Checksum mismatch for {rel}: the source no longer matches the frozen data.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        fetched += 1
    print(f"Raw data verified: {kept} already present, {fetched} downloaded, "
          f"{len(manifest['files'])} total")


if __name__ == "__main__":
    main()
