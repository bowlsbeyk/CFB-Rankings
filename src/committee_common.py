"""Shared inputs for T7 and T8 (DEVIATIONS.md, 2026-11-05).

frames():          T5's per-week results-only ranks for 2014-2025 (src/sor_test.py run_season,
                   unchanged), with the 11 strength-of-record settings ranked, Colley and
                   performance ranks, and the AP poll released after each schedule week.
committee_ranks(): the Playoff Committee Rankings from the frozen raw poll files,
                   {season: {label_week: {school: rank}}}. Committee ranking c reflects games
                   through schedule week c - 1, the same timing as AP poll c.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sor_test import HIST, TABLE, offsets_from_t4, run_season, variants  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "polls"
POWER_OTHERS = ["ACC", "Big Ten", "Big 12", "Pac-12"]


def frames():
    tw = pd.read_csv(TABLE)
    offsets = offsets_from_t4()
    allw = pd.concat([run_season(s, tw, offsets)[0] for s in HIST], ignore_index=True)
    g = allw.groupby(["season", "week"])
    for nm, *_ in variants():
        allw[f"sor_rank_{nm}"] = g[f"sor_{nm}"].rank(method="average")
    allw["colley_rank"] = g.colley.rank(ascending=False, method="average")
    allw["perf_rank"] = g.performance.rank(ascending=False, method="average")
    return allw


def committee_ranks():
    out = {}
    for s in HIST:
        data = json.loads((RAW / f"rankings_{s}_regular.json").read_text())
        out[s] = {}
        for w in data:
            for p in w["polls"]:
                if p["poll"] == "Playoff Committee Rankings":
                    out[s][w["week"]] = {r["school"]: r["rank"] for r in p["ranks"]}
    return out


def ap_ranks():
    """{season: {label_week: {school: rank}}} for the AP poll, from the same raw files."""
    out = {}
    for s in HIST:
        data = json.loads((RAW / f"rankings_{s}_regular.json").read_text())
        out[s] = {}
        for w in data:
            for p in w["polls"]:
                if p["poll"] == "AP Top 25":
                    out[s][w["week"]] = {r["school"]: r["rank"] for r in p["ranks"]}
    return out


def committee_frames(allw, cfp):
    """One frame per committee ranking: results through week c - 1, with the committee rank in
    `ap_rank` (so T5's counting functions apply unchanged) and the AP rank of the same label week
    in `ap_same_week`. Also returns the committee schools that matched no team."""
    ap = ap_ranks()
    rows, unmatched = [], set()
    for s, weeks in cfp.items():
        for c, ranks in weeks.items():
            d = allw[(allw.season == s) & (allw.week == c - 1)].copy()
            if d.empty:
                continue
            unmatched |= {f"{s}:{t}" for t in ranks if t not in set(d.team)}
            d["cfp_week"] = c
            d["ap_rank"] = d.team.map(ranks)
            d["ap_same_week"] = d.team.map(ap[s].get(c, {}))
            rows.append(d)
    return pd.concat(rows, ignore_index=True), sorted(unmatched)
