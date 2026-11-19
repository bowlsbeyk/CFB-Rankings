"""Post hoc: T8's same-résumé test at season's end, matched on ESPN's strength of record
(DEVIATIONS.md, 2026-11-19, logged after T9/T10 results, before this ran).

Each team of the focal conference in ESPN's final strength-of-record top 30 is matched with the
team from the other power conferences with the same number of losses (full season, bowls
included) and the nearest ESPN strength-of-record rank within 3 (ties averaged). Outcome: rank
points in the final AP poll (after the bowls), focal minus match. Writes results/t8_espn_matched.json.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from matched_test import reading  # noqa: E402
from sor_test import HIST, group_of, tstats  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "results" / "t8_espn_matched.json"
POWER = ["SEC", "ACC", "Big Ten", "Big 12", "Pac-12"]


def season_table(s):
    g = pd.read_parquet(RAW / "schedules" / f"cfb_schedules_{s}.parquet")
    g = g[g.season_type.isin(["regular", "postseason"]) & g.completed]
    rows = []
    for x in g.itertuples():
        for t, c, pf, pa in ((x.home_team, x.home_conference, x.home_points, x.away_points),
                             (x.away_team, x.away_conference, x.away_points, x.home_points)):
            rows.append((t, c, int(pf < pa)))
    d = pd.DataFrame(rows, columns=["team", "conference", "loss"])
    conf = d.groupby("team").conference.agg(lambda v: v.mode().iat[0])
    losses = d.groupby("team").loss.sum()
    fpi = json.loads((RAW / "advanced" / f"fpi_{s}.json").read_text())
    sor = pd.Series({x["team"]: (x.get("resumeRanks") or {}).get("strengthOfRecord") for x in fpi}, dtype=float)
    post = json.loads((RAW / "polls" / f"rankings_{s}_postseason.json").read_text())
    ap = {r["school"]: r["rank"] for w in post for p in w["polls"] if p["poll"] == "AP Top 25" for r in p["ranks"]}
    t = pd.DataFrame({"espn_sor": sor}).join(losses.rename("losses")).join(conf.rename("conference"))
    t["group"] = [group_of(c, team, s) for team, c in zip(t.index, t.conference)]
    t["pts"] = [max(0, 26 - ap[team]) if team in ap else 0 for team in t.index]
    return t.dropna(subset=["espn_sor", "losses"])


def run(tables, focal):
    others = [g for g in POWER if g != focal]
    per, n = [], 0
    for s in HIST:
        t = tables[s]
        foc, pool = t[(t.group == focal) & (t.espn_sor <= 30)], t[t.group.isin(others)]
        diffs = []
        for team, x in foc.iterrows():
            c = pool[(pool.losses == x.losses) & ((pool.espn_sor - x.espn_sor).abs() <= 3)]
            if c.empty:
                continue
            gap = (c.espn_sor - x.espn_sor).abs()
            diffs.append(x.pts - c[gap == gap.min()].pts.mean())
        n += len(diffs)
        per.append(np.mean(diffs) if diffs else np.nan)
    v = [x for x in per if not np.isnan(x)]
    st = tstats(v)
    return {**{k: st[k] for k in ("mean", "ci95_t", "ci90_t", "seasons_positive", "seasons", "sign_flip_p")},
            "pairs": n, "reading": reading(st)}


def main():
    tables = {s: season_table(s) for s in HIST}
    report = {"note": "post hoc; final AP poll and ESPN final strength of record; DEVIATIONS.md 2026-11-19"}
    for g in POWER:
        report[g] = run(tables, g)
        r = report[g]
        print(f"{g:8s} {r['mean']:+.2f} ({r['ci95_t'][0]:+.2f} to {r['ci95_t'][1]:+.2f}; "
              f"{r['seasons_positive']}/{r['seasons']}; {r['pairs']} pairs) -> {r['reading']}")
    OUT.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
