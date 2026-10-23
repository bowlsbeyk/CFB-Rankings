"""Checks on the frozen raw data. Fails loudly on any problem; offline only.

1. Checksums in data/MANIFEST.json match the files on disk.
2. AP poll depth: how many teams each CFBD AP poll lists (25 plus ties at #25).
3. Name matching: every AP-ranked school appears in that season's schedule.
4. Preseason: a week-1 AP poll exists for every season.
"""

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SEASONS = range(2014, 2027)


def ap_polls(season, season_type):
    path = ROOT / "data" / "raw" / "polls" / f"rankings_{season}_{season_type}.json"
    for week in json.loads(path.read_text()):
        for poll in week["polls"]:
            if poll["poll"] == "AP Top 25":
                yield week["week"], poll["ranks"]


def main():
    manifest = json.loads((ROOT / "data" / "MANIFEST.json").read_text())
    for rel, meta in manifest["files"].items():
        digest = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        if digest != meta["sha256"]:
            sys.exit(f"Checksum mismatch: {rel}")
    print(f"Checksums OK for {len(manifest['files'])} files")

    over_25, unmatched, no_preseason = [], {}, []
    for season in SEASONS:
        sched = pd.read_parquet(
            ROOT / "data" / "raw" / "schedules" / f"cfb_schedules_{season}.parquet")
        teams = set(sched.home_team) | set(sched.away_team)
        weeks = set()
        for season_type in ("regular", "postseason"):
            for week, ranks in ap_polls(season, season_type):
                if season_type == "regular":
                    weeks.add(week)
                if max(r["rank"] for r in ranks) > 25:
                    sys.exit(f"Rank beyond 25 in {season} {season_type} week {week}")
                if len(ranks) != 25:
                    over_25.append((season, season_type, week, len(ranks)))
                for r in ranks:
                    if r["school"] not in teams:
                        unmatched.setdefault(r["school"], []).append(season)
        if 1 not in weeks:
            no_preseason.append(season)

    print("AP polls list ranks 1-25 only; polls with ties at #25:", over_25)
    if unmatched:
        sys.exit(f"AP schools missing from schedules: {unmatched}")
    print("All AP schools match a schedule team")
    if no_preseason:
        sys.exit(f"No week-1 (preseason) AP poll for: {no_preseason}")
    print("Week-1 (preseason) AP poll present for every season")


if __name__ == "__main__":
    main()
