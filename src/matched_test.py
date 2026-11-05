"""T8: same résumé, different conference (DEVIATIONS.md, 2026-11-05).

In every AP poll from poll 6 on, each SEC team in the strength-of-record top 30 is matched with
the team from the other power conferences (ACC, Big Ten, Big 12, Pac-12 when present) that has
the same number of losses and the nearest strength-of-record rank, within 3 places (ties for
nearest averaged). Matching uses results only. Outcome: AP rank points in the poll released
after that week (26 - rank inside the top 25, 0 outside), SEC team minus match: positive = the
SEC team is ranked higher than a non-SEC team with the same losses and nearly the same record.
M_SEC is the per-season mean over pairs, tested across 2014-2025 (no 2020) with T5's statistics.

Writes results/t8_matched.json and results/t8_pairs.csv (every primary pair; no poll points,
only the derived rank difference).
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from committee_common import POWER_OTHERS, committee_frames, committee_ranks, frames  # noqa: E402
from sor_test import HIST, PRIMARY, tstats  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "t8_matched.json"
PAIRS = ROOT / "results" / "t8_pairs.csv"
PRIM_RANK = f"sor_rank_{PRIMARY[0]}|x{PRIMARY[1]}"
TOP = 30
WINDOW = 3


def points(rank):
    r = pd.to_numeric(rank, errors="coerce")
    return np.where(r.notna() & (r <= 25), 26 - r.fillna(26), 0.0)


def match_week(d, rank_col, window, opp_groups, outcome, sec_band=None):
    """Pairs for one poll week. outcome: 'points' (rank points) or 'capped' (rank capped at 26)."""
    d = d.copy()
    d["pts"] = points(d.ap_rank)
    d["capped"] = pd.to_numeric(d.ap_rank, errors="coerce").fillna(26).clip(upper=26)
    sec = d[(d.group == "SEC") & (d[rank_col] <= TOP)]
    if sec_band:
        sec = sec[sec[rank_col].between(*sec_band)]
    pool = d[d.group.isin(opp_groups)]
    rows = []
    for _, t in sec.iterrows():
        c = pool[(pool.losses == t.losses) & ((pool[rank_col] - t[rank_col]).abs() <= window)]
        if c.empty:
            rows.append({"team": t.team, "matched": False})
            continue
        gap = (c[rank_col] - t[rank_col]).abs()
        best = c[gap == gap.min()]
        if outcome == "points":
            diff = float(t.pts - best.pts.mean())
        else:
            diff = float(best.capped.mean() - t.capped)
        rows.append({"team": t.team, "matched": True, "diff": diff,
                     "rank_gap": float((best[rank_col] - t[rank_col]).mean()),
                     "match": ";".join(best.team), "losses": int(t.losses), "sec_rank": float(t[rank_col])})
    return rows


def run(allw, rank_col=PRIM_RANK, window=WINDOW, opp_groups=POWER_OTHERS, outcome="points",
        sec_band=None, keep=False):
    per_season, pairs, n_all, n_matched, gaps = [], [], 0, 0, []
    for s in HIST:
        vals = []
        for w, d in allw[allw.season == s].groupby("week"):
            for r in match_week(d, rank_col, window, opp_groups, outcome, sec_band):
                n_all += 1
                if r["matched"]:
                    n_matched += 1
                    vals.append(r["diff"])
                    gaps.append(r["rank_gap"])
                    if keep:
                        pairs.append({"season": s, "week": int(w), **r})
        per_season.append(float(np.mean(vals)) if vals else np.nan)
    out = tstats([v for v in per_season if not np.isnan(v)])
    out["seasons_with_pairs"] = int(np.sum(~np.isnan(per_season)))
    out["pairs"] = n_matched
    out["sec_team_weeks"] = n_all
    out["share_matched"] = n_matched / n_all if n_all else None
    out["mean_rank_gap_match_minus_sec"] = float(np.mean(gaps)) if gaps else None
    return (out, pairs) if keep else out


def reading(x):
    if x["ci95_t"][0] > 0 and x["seasons_positive"] >= 9:
        return "SEC NAME PREMIUM SHOWN"
    if x["ci90_t"][0] >= -1 and x["ci90_t"][1] <= 1:
        return "NO PREMIUM BEYOND ONE PLACE"
    if x["ci95_t"][1] < 0 and x["seasons_positive"] <= 2:
        return "SEC PENALTY SHOWN"
    return "INCONCLUSIVE"


def main():
    allw = frames()
    prim, pairs = run(allw, keep=True)
    report = {"primary_M_SEC": prim, "reading": reading(prim),
              "unit": "AP poll places (rank points); positive = SEC team ranked higher than its match"}

    checks = {
        "window +/-2": run(allw, window=2),
        "window +/-5": run(allw, window=5),
        "match on Colley rank": run(allw, rank_col="colley_rank"),
        "SOR, T4 all-games calibration": run(allw, rank_col="sor_rank_top25|x1.0|t4_all"),
        "SOR, T4 power-games calibration": run(allw, rank_col="sor_rank_top25|x1.0|t4_power"),
        "outcome: AP rank capped at 26": run(allw, outcome="capped"),
    }
    flips = [k for k, v in checks.items() if np.sign(v["mean"]) != np.sign(prim["mean"])]
    report["robustness"] = {"by_check": {k: {"mean": v["mean"], "ci95_t": v["ci95_t"],
                                             "seasons_positive": v["seasons_positive"], "pairs": v["pairs"]}
                                         for k, v in checks.items()},
                            "sign_flips_under": flips, "robust": not flips,
                            "rule": "the premium reading is robust only if M_SEC keeps its sign in every check"}

    sec_acc = run(allw, opp_groups=["ACC"])
    report["secondary_M_ACC"] = {**sec_acc, "reading": reading(sec_acc)}
    cf, _ = committee_frames(allw, committee_ranks())
    cfp = run(cf)
    report["secondary_M_CFP_committee"] = {**cfp, "reading": reading(cfp)}
    bub = run(allw, sec_band=(6, 16))
    report["secondary_M_BUBBLE_sor_6_16"] = {**bub, "reading": reading(bub)}

    pd.DataFrame(pairs).to_csv(PAIRS, index=False)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)} and {PAIRS.relative_to(ROOT)}")
    for k, v in [("M_SEC", prim), ("M_ACC", sec_acc), ("M_CFP", cfp), ("M_BUBBLE", bub)]:
        print(f"  {k}: {v['mean']:+.2f} (95% t {v['ci95_t'][0]:+.2f} to {v['ci95_t'][1]:+.2f}; "
              f"{v['seasons_positive']}/{v['seasons_with_pairs']} seasons; {v['pairs']} pairs, "
              f"{v['share_matched']:.0%} matched, gap {v['mean_rank_gap_match_minus_sec']:+.2f}) -> {reading(v)}")
    for k, v in checks.items():
        print(f"  check {k}: {v['mean']:+.2f} ({v['ci95_t'][0]:+.2f} to {v['ci95_t'][1]:+.2f})")
    print("  robust:", not flips, flips)


if __name__ == "__main__":
    main()
