"""Pull ESPN FPI, SP+ and per-game EPA from CollegeFootballData.com (DEVIATIONS.md, 2026-11-19).

Writes data/raw/advanced/{fpi,sp,ppa_games}_{season}.json (not committed) and records each file
in data/MANIFEST.json with its source URL and checksum, so src/fetch_data.py can rebuild them.
The 2026 EPA file is cut to weeks <= the frozen AP week minus one (games through the last frozen
schedule week); the 2026 FPI and SP+ files are snapshots the source will overwrite.

Needs CFBD_API_KEY. Never prints it.
"""

import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "advanced"
MANIFEST = ROOT / "data" / "MANIFEST.json"
BASE = "https://api.collegefootballdata.com"
SEASONS = [s for s in range(2014, 2027) if s != 2020]
LAST_2026_WEEK = 11


def get(path):
    key = os.environ.get("CFBD_API_KEY")
    if not key:
        sys.exit("CFBD_API_KEY is not set.")
    req = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:
            if attempt == 3:
                sys.exit(f"CFBD request failed for {path.split('?')[0]}: {type(e).__name__}")
            time.sleep(2 ** (attempt + 1))


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text())
    for s in SEASONS:
        for name, path in (("fpi", f"/ratings/fpi?year={s}"), ("sp", f"/ratings/sp?year={s}"),
                           ("ppa_games", f"/ppa/games?year={s}&seasonType=regular")):
            body = get(path)
            meta = {"source_url": BASE + path}
            data = json.loads(body)
            if s == 2026 and name == "ppa_games":
                data = [g for g in data if g["week"] <= LAST_2026_WEEK]
                body = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
                meta["frozen_through_week"] = LAST_2026_WEEK
            elif s == 2026:
                meta["snapshot"] = "2026-11-19"
            dst = RAW / f"{name}_{s}.json"
            dst.write_bytes(body)
            meta.update({"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)})
            manifest["files"][str(dst.relative_to(ROOT))] = meta
            print(f"{dst.relative_to(ROOT)}: {len(data)} rows")
    manifest["files"] = dict(sorted(manifest["files"].items()))
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
