"""Post hoc checks prompted by independent review of T8 (DEVIATIONS.md, 2026-11-19).

On T8's pairs (same losses, strength of record within 3 places, focal team in the SOR top 30;
outcome AP rank points, focal minus match), for each power conference as the focal group:
  1. intercept after allowing for how the season ended (current SOR gap, current margin-rank gap,
     end-of-regular-season SOR gap), per-season regressions, T5 statistics across seasons;
  2. intercept after a continuous preseason AP gap (unranked = 26), per-season regressions;
  3. T8 at each season's last regular-season week only (our yardstick at season's end);
  4. SEC pairs split by the match's conference.
Writes results/t8_verification.json.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from committee_common import ap_ranks, frames  # noqa: E402
from matched_test import PRIM_RANK, TOP, WINDOW, points  # noqa: E402
from sor_test import HIST, tstats  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "t8_verification.json"
POWER = ["SEC", "ACC", "Big Ten", "Big 12", "Pac-12"]
KEEP = ("mean", "ci95_t", "seasons_positive", "seasons", "sign_flip_p")


def pairs(allw, focal):
    pre = {s: wk.get(1, {}) for s, wk in ap_ranks().items()}
    last = allw.groupby("season").week.max()
    final = allw[allw.week == allw.season.map(last)].set_index(["season", "team"])[PRIM_RANK]
    pool_groups = [g for g in POWER if g != focal]
    rows = []
    for (s, w), d in allw.groupby(["season", "week"]):
        d = d.assign(pts=points(d.ap_rank))
        foc = d[(d.group == focal) & (d[PRIM_RANK] <= TOP)]
        pool = d[d.group.isin(pool_groups)]
        for _, t in foc.iterrows():
            c = pool[(pool.losses == t.losses) & ((pool[PRIM_RANK] - t[PRIM_RANK]).abs() <= WINDOW)]
            if c.empty:
                continue
            gap = (c[PRIM_RANK] - t[PRIM_RANK]).abs()
            b = c[gap == gap.min()]
            rows.append({
                "season": s, "week": int(w), "last_week": int(w) == int(last[s]), "team": t.team,
                "diff": float(t.pts - b.pts.mean()),
                "sor_gap": float((b[PRIM_RANK] - t[PRIM_RANK]).mean()),
                "perf_gap": float((b.perf_rank - t.perf_rank).mean()),
                "final_sor_gap": float(np.mean([final[(s, m)] for m in b.team]) - final[(s, t.team)]),
                "pre_gap": float(np.mean([pre[s].get(m, 26) for m in b.team]) - pre[s].get(t.team, 26)),
                "match_groups": ";".join(sorted(set(b.group)))})
    return pd.DataFrame(rows)


def intercepts(p, cols):
    vals = []
    for s in HIST:
        q = p[p.season == s]
        if len(q) < len(cols) + 3:
            continue
        X = np.column_stack([np.ones(len(q))] + [q[c].to_numpy() for c in cols])
        vals.append(np.linalg.lstsq(X, q["diff"].to_numpy(), rcond=None)[0][0])
    st = tstats(vals)
    return {k: st[k] for k in KEEP}


def season_mean(p):
    v = p.groupby("season")["diff"].mean().reindex(HIST).dropna()
    st = tstats(v.tolist())
    return {**{k: st[k] for k in KEEP}, "pairs": int(len(p))}


def main():
    allw = frames()
    rep = {"note": "post hoc; DEVIATIONS.md 2026-11-19 (independent verification)"}
    for g in POWER:
        p = pairs(allw, g)
        X = np.column_stack([np.ones(len(p)), p.pre_gap])
        slope = float(np.linalg.lstsq(X, p["diff"].to_numpy(), rcond=None)[0][1])
        rep[g] = {
            "t8_reproduced": season_mean(p),
            "mean_final_sor_gap_match_minus_focal": float(p.final_sor_gap.mean()),
            "1_allowing_for_how_season_ended": intercepts(p, ["sor_gap", "perf_gap", "final_sor_gap"]),
            "2_preseason_gap_held_fixed": {**intercepts(p, ["pre_gap"]), "pooled_slope_per_preseason_place": slope},
            "3_last_regular_season_week_only": season_mean(p[p.last_week]),
        }
        if g == "SEC":
            rep["4_SEC_by_match_conference"] = {
                m: season_mean(p[p.match_groups == m]) for m in ["ACC", "Big Ten", "Big 12", "Pac-12"]}
    OUT.write_text(json.dumps(rep, indent=2) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    f = lambda x: f"{x['mean']:+.2f} ({x['ci95_t'][0]:+.2f} to {x['ci95_t'][1]:+.2f}; {x['seasons_positive']}/{x['seasons']})"
    for g in POWER:
        r = rep[g]
        print(f"{g:8s} T8 {f(r['t8_reproduced'])} | ended {f(r['1_allowing_for_how_season_ended'])} | "
              f"preseason fixed {f(r['2_preseason_gap_held_fixed'])} slope {r['2_preseason_gap_held_fixed']['pooled_slope_per_preseason_place']:.2f} | "
              f"last week {f(r['3_last_regular_season_week_only'])} | final gap {r['mean_final_sor_gap_match_minus_focal']:+.2f}")
    for m, x in rep["4_SEC_by_match_conference"].items():
        print(f"  SEC vs {m}: {f(x)} pairs {x['pairs']}")


if __name__ == "__main__":
    main()
