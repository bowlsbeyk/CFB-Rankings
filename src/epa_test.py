"""T10: EPA per play as a third results-only yardstick (DEVIATIONS.md, 2026-11-19).

Rating after each schedule week, from that season's regular-season games so far: one row per game,
net EPA per play (offense EPA/play minus defense EPA/play allowed) from the home team's side, or the
FBS team's side against a pooled FCS opponent; least squares net = r_home - r_away + h*home with one
zero-net pseudo-game per team (src/sor_test.py performance_fast, unchanged). Games without EPA data
are left out of this rating only.

Primary: T8's pairs (same losses, strength of record within 3, SEC team in the strength-of-record
top 30) restricted to pairs whose EPA ranks are within 10 places (M_SEC_EPA). Secondary: matching on
EPA instead of strength of record (same losses, EPA rank within 5); the placebo with EPA held fixed.
Descriptive: EPA top-25 slots against AP top-25 slots by group, polls 6+.

Writes results/t10_epa.json and results/epa_weekly.csv (derived EPA ranks only).
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from committee_common import frames  # noqa: E402
from matched_test import PRIM_RANK, TOP, WINDOW, points, reading  # noqa: E402
from sor_test import (FCS, FIRST_WEEK, HIST, performance_fast, quantities, season_excess,  # noqa: E402
                      season_games, tstats)

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "advanced"
OUT = ROOT / "results" / "t10_epa.json"
WEEKLY = ROOT / "results" / "epa_weekly.csv"
POWER = ["SEC", "ACC", "Big Ten", "Big 12", "Pac-12"]
EPA_WINDOW = 10


def epa_ratings(season, weeks):
    g, _ = season_games(season)
    ppa = json.loads((RAW / f"ppa_games_{season}.json").read_text())
    net = {(x["gameId"], x["team"]): x["offense"]["overall"] - x["defense"]["overall"]
           for x in ppa if x.get("offense", {}).get("overall") is not None
           and x.get("defense", {}).get("overall") is not None}
    rows = []
    for x in g.itertuples():
        if x.home != FCS and (x.game_id, x.home) in net:
            v = net[(x.game_id, x.home)]
        elif x.away != FCS and (x.game_id, x.away) in net:
            v = -net[(x.game_id, x.away)]
        else:
            continue
        rows.append((x.week, x.home, x.away, 0.0 if x.neutral_site else 1.0, v))
    e = pd.DataFrame(rows, columns=["week", "home", "away", "venue", "net"])
    teams = sorted((set(g.home) | set(g.away)) - {FCS}) + [FCS]
    idx = {t: i for i, t in enumerate(teams)}
    out = []
    for w in weeks:
        p = e[e.week <= w]
        r, _ = performance_fast(p.home.map(idx).to_numpy(), p.away.map(idx).to_numpy(), p.venue.to_numpy(),
                                p.net.to_numpy(), len(teams))
        d = pd.DataFrame({"season": season, "week": w, "team": teams[:-1], "epa_rating": r[:-1]})
        d["epa_rank"] = d.epa_rating.rank(ascending=False, method="average")
        out.append(d)
    return pd.concat(out), len(e), len(g)


def match(allw, focal="SEC", rank_col=PRIM_RANK, window=WINDOW, epa_window=None, sec_top=TOP):
    pool_groups = [x for x in POWER if x != focal]
    rows = []
    for (s, w), d in allw.groupby(["season", "week"]):
        d = d.assign(pts=points(d.ap_rank))
        foc = d[(d.group == focal) & (d[PRIM_RANK] <= sec_top)]
        pool = d[d.group.isin(pool_groups)]
        for _, t in foc.iterrows():
            c = pool[(pool.losses == t.losses) & ((pool[rank_col] - t[rank_col]).abs() <= window)]
            if epa_window is not None:
                c = c[(c.epa_rank - t.epa_rank).abs() <= epa_window]
            if c.empty:
                continue
            gap = (c[rank_col] - t[rank_col]).abs()
            b = c[gap == gap.min()]
            rows.append({"season": s, "diff": float(t.pts - b.pts.mean()),
                         "epa_gap": float((b.epa_rank - t.epa_rank).mean()),
                         "sor_gap": float((b[PRIM_RANK] - t[PRIM_RANK]).mean())})
    p = pd.DataFrame(rows)
    v = p.groupby("season")["diff"].mean().reindex(HIST).dropna()
    st = tstats(v.tolist())
    keep = ("mean", "ci95_t", "ci90_t", "seasons_positive", "seasons", "sign_flip_p")
    return {**{k: st[k] for k in keep}, "pairs": int(len(p)), "mean_epa_gap_match_minus_focal": float(p.epa_gap.mean()),
            "mean_sor_gap_match_minus_focal": float(p.sor_gap.mean())}


def main():
    allw = frames()
    epa, cover = [], {}
    for s in HIST:
        weeks = sorted(allw[allw.season == s].week.unique())
        d, n_epa, n_games = epa_ratings(s, weeks)
        epa.append(d)
        cover[str(s)] = {"games_with_epa": n_epa, "games": n_games}
    epa = pd.concat(epa)
    epa.to_csv(WEEKLY, index=False, float_format="%.6f")
    allw = allw.merge(epa[["season", "week", "team", "epa_rank"]], on=["season", "week", "team"], how="left")

    base = match(allw)
    prim = match(allw, epa_window=EPA_WINDOW)
    report = {"coverage": cover, "t8_primary_reproduced": base,
              "primary_M_SEC_EPA": {**prim, "reading": reading(prim),
                                    "share_of_t8_pairs_kept": prim["pairs"] / base["pairs"]}}
    sec = match(allw, rank_col="epa_rank", window=5)
    report["secondary_match_on_EPA_instead"] = {**sec, "reading": reading(sec)}
    report["secondary_placebo_EPA_held_fixed"] = {}
    for g in POWER:
        x = match(allw, focal=g, epa_window=EPA_WINDOW)
        report["secondary_placebo_EPA_held_fixed"][g] = {**x, "reading": reading(x)}

    per = {s: season_excess(allw[allw.season == s], "epa_rank", True) for s in HIST}
    report["descriptive_EPA_top25_vs_AP"] = {k: tstats(v) for k, v in quantities(per).items()}
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print("coverage:", {k: f"{v['games_with_epa']}/{v['games']}" for k, v in cover.items()})
    for k, v in [("T8 reproduced", base), ("M_SEC_EPA", prim), ("match on EPA", sec)]:
        print(f"  {k}: {v['mean']:+.2f} ({v['ci95_t'][0]:+.2f} to {v['ci95_t'][1]:+.2f}; {v['seasons_positive']}/{v['seasons']}; "
              f"{v['pairs']} pairs; epa gap {v['mean_epa_gap_match_minus_focal']:+.2f}) -> {reading(v)}")
    for g, v in report["secondary_placebo_EPA_held_fixed"].items():
        print(f"  placebo {g}: {v['mean']:+.2f} ({v['ci95_t'][0]:+.2f} to {v['ci95_t'][1]:+.2f}) -> {v['reading']}")
    e = report["descriptive_EPA_top25_vs_AP"]
    print("  AP minus EPA top-25 slots:", {k: round(v["mean"], 2) for k, v in e.items()})


if __name__ == "__main__":
    main()
