"""Post hoc checks of T8 (DEVIATIONS.md, 2026-11-05, logged after T7/T8 results, before these ran).

1. Margin held fixed too: T8's match plus performance (schedule-adjusted margin) rank within 10.
2. Regression adjustment: AP difference on the pairs' strength-of-record and performance gaps.
3. Placebo: each power conference as the focal group, matched against the other power
   conferences (the SEC included).
4. Descriptive: split by preseason AP rank (focal higher or not) and by stage of the season.

Writes results/t8_posthoc.json.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from committee_common import ap_ranks, frames  # noqa: E402
from matched_test import PRIM_RANK, TOP, WINDOW, points, reading  # noqa: E402
from sor_test import HIST, tstats  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "t8_posthoc.json"
POWER = ["SEC", "ACC", "Big Ten", "Big 12", "Pac-12"]


def pairs(allw, focal="SEC", perf_window=None):
    pool_groups = [g for g in POWER if g != focal]
    pre = {s: wk.get(1, {}) for s, wk in ap_ranks().items()}
    rows = []
    for (s, w), d in allw.groupby(["season", "week"]):
        d = d.assign(pts=points(d.ap_rank))
        foc = d[(d.group == focal) & (d[PRIM_RANK] <= TOP)]
        pool = d[d.group.isin(pool_groups)]
        for _, t in foc.iterrows():
            c = pool[(pool.losses == t.losses) & ((pool[PRIM_RANK] - t[PRIM_RANK]).abs() <= WINDOW)]
            if perf_window is not None:
                c = c[(c.perf_rank - t.perf_rank).abs() <= perf_window]
            if c.empty:
                continue
            gap = (c[PRIM_RANK] - t[PRIM_RANK]).abs()
            b = c[gap == gap.min()]
            pre_t = pre[s].get(t.team, 26)
            pre_m = np.mean([pre[s].get(x, 26) for x in b.team])
            rows.append({"season": s, "week": int(w), "diff": float(t.pts - b.pts.mean()),
                         "sor_gap": float((b[PRIM_RANK] - t[PRIM_RANK]).mean()),
                         "perf_gap": float((b.perf_rank - t.perf_rank).mean()),
                         "preseason_higher": bool(pre_t < pre_m)})
    return pd.DataFrame(rows)


def season_stat(df):
    v = df.groupby("season")["diff"].mean().reindex(HIST).dropna()
    out = tstats(v.tolist())
    out["pairs"] = int(len(df))
    out["seasons_with_pairs"] = int(len(v))
    return out


def brief(x):
    return {k: x[k] for k in ("mean", "ci95_t", "seasons_positive", "seasons", "sign_flip_p", "pairs")}


def main():
    allw = frames()
    base = pairs(allw)
    report = {"note": "post hoc; see DEVIATIONS.md 2026-11-05", "primary_reproduced": brief(season_stat(base))}

    m = pairs(allw, perf_window=10)
    s1 = season_stat(m)
    report["1_margin_held_fixed"] = {**brief(s1), "reading": reading(s1),
                                     "mean_perf_gap": float(m.perf_gap.mean()), "mean_sor_gap": float(m.sor_gap.mean())}

    X = np.column_stack([np.ones(len(base)), base.sor_gap, base.perf_gap])
    coef, *_ = np.linalg.lstsq(X, base["diff"].to_numpy(), rcond=None)
    rng = np.random.default_rng(0)
    boots = []
    seasons = np.array(HIST)
    for _ in range(1000):
        pick = rng.choice(seasons, len(seasons))
        b = pd.concat([base[base.season == s] for s in pick])
        Xb = np.column_stack([np.ones(len(b)), b.sor_gap, b.perf_gap])
        boots.append(np.linalg.lstsq(Xb, b["diff"].to_numpy(), rcond=None)[0])
    boots = np.array(boots)
    report["2_regression_adjusted"] = {
        "intercept_premium": float(coef[0]), "intercept_ci95_season_bootstrap": np.percentile(boots[:, 0], [2.5, 97.5]).tolist(),
        "per_sor_place_of_gap": float(coef[1]), "per_perf_place_of_gap": float(coef[2]),
        "mean_perf_gap_match_minus_sec": float(base.perf_gap.mean()),
        "note": "gaps are match rank minus SEC rank (positive = match worse); intercept = premium at zero gap"}

    report["3_placebo_focal_conference"] = {}
    for g in POWER:
        st = season_stat(pairs(allw, focal=g))
        report["3_placebo_focal_conference"][g] = {**brief(st), "reading": reading(st)}

    report["4_descriptive"] = {
        "sec_preseason_ranked_higher": brief(season_stat(base[base.preseason_higher])),
        "sec_preseason_not_higher": brief(season_stat(base[~base.preseason_higher])),
        "share_pairs_sec_preseason_higher": float(base.preseason_higher.mean()),
        "by_stage": {}}
    for name, lo, hi in (("polls 6-8", 5, 7), ("polls 9-11", 8, 10), ("polls 12+", 11, 99)):
        report["4_descriptive"]["by_stage"][name] = brief(season_stat(base[base.week.between(lo, hi)]))

    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(json.dumps(report, indent=1)[:4000])


if __name__ == "__main__":
    main()
