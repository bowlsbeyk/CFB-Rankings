"""Pull postseason games from CollegeFootballData.com for 2014-2025 (no 2020) into
data/raw/postseason/ (not committed) and record checksums in data/MANIFEST.json
(DEVIATIONS.md, 2026-11-19). Needs CFBD_API_KEY; never prints it."""

import hashlib
import json
from pathlib import Path

from pull_advanced import BASE, MANIFEST, get

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "postseason"
SEASONS = [s for s in range(2014, 2026) if s != 2020]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text())
    for s in SEASONS:
        path = f"/games?year={s}&seasonType=postseason"
        body = get(path)
        dst = RAW / f"games_{s}_postseason.json"
        dst.write_bytes(body)
        manifest["files"][str(dst.relative_to(ROOT))] = {
            "source_url": BASE + path, "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
        print(f"{dst.relative_to(ROOT)}: {len(json.loads(body))} games")
    manifest["files"] = dict(sorted(manifest["files"].items()))
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
