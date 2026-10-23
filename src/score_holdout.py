"""Score the 2024-2025 holdout once, with the models frozen in train.py.

For every spec (registered, revised) and unranked treatment (zero, floor):
  1. Team-week MAE on the holdout for baseline, linear and challenger.
  2. Model choice by the pre-registered rule: challenger only if its holdout MAE
     is more than 10% below linear's.
  3. Pass criteria: the chosen model beats the baseline on MAE, and its replay of
     each holdout season (from the real preseason poll) reaches Spearman >= 0.7
     against the final regular-season AP poll (definition in DEVIATIONS.md).

The first run writes results/holdout.json. Later runs (e.g. run_all.py) recompute
and fail if any number differs from the recorded one; they never overwrite it.
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from replay import compare, preseason_ranks, real_poll, replay, start_values, stickiness
from train import TREATMENTS, UNIT, features, target

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
RESULTS = ROOT / "results"
OUT = RESULTS / "holdout.json"
HOLDOUT = [2024, 2025]
PRIMARY = ("revised", "zero")
# The specs scored on the clean holdout. The rated spec came later; its 2024-2025
# numbers are a re-used holdout and live in evaluate_rated.py (DEVIATIONS.md).
SCORED_SPECS = ("registered", "revised")


def mae(y, p):
    return float(np.mean(np.abs(y - p)))


def score(tw, spec, tr):
    hold = tw[tw.season.isin(HOLDOUT)]
    X, y = hold[features(tr, spec)], hold[target(tr, spec)]
    models = {n: joblib.load(RESULTS / "models" / f"{n}_{spec}_{tr}.joblib")
              for n in ("linear", "gbt")}
    preds = {"baseline": np.zeros(len(y)), **{n: m.predict(X) for n, m in models.items()}}
    ranked = hold.prior_rank.notna().to_numpy()
    res = {
        "unit": UNIT[spec],
        "mae": {n: mae(y, p) for n, p in preds.items()},
        "mae_ranked_teams": {n: mae(y[ranked], p[ranked]) for n, p in preds.items()},
        "mae_by_season": {str(s): {n: mae(y[(hold.season == s).to_numpy()],
                                          p[(hold.season == s).to_numpy()])
                                   for n, p in preds.items()} for s in HOLDOUT},
    }
    chosen = "gbt" if res["mae"]["gbt"] < 0.9 * res["mae"]["linear"] else "linear"
    res["chosen_model"] = chosen

    replays = {}
    for season in HOLDOUT:
        rows = hold[hold.season == season]
        start = start_values(season, spec)
        polls = replay(rows, models[chosen], tr, start, spec)
        final_week = max(polls)
        final_real = real_poll(season, final_week)
        sim = polls[final_week].sim_rank
        r = {
            "final_regular": compare(sim, final_real),
            "preseason_unchanged_vs_final_regular":
                compare(preseason_ranks(rows, start), final_real),
            "post_bowl_final": compare(sim, real_poll(season, season_type="postseason")),
            "stickiness": stickiness(sim, final_real, start),
            "sim_top25": list(sim.nsmallest(25).index),
            "real_top25": [t for t, _ in sorted(final_real.items(),
                                                key=lambda kv: kv[1]["rank"])],
        }
        replays[str(season)] = r
    res["replay"] = replays
    beats = res["mae"][chosen] < res["mae"]["baseline"]
    spear = all(replays[str(s)]["final_regular"]["spearman"] >= 0.7 for s in HOLDOUT)
    res["pass"] = {"beats_baseline_mae": beats, "spearman_ge_0.7_both_seasons": spear,
                   "passed": bool(beats and spear)}
    return res


def main():
    tw = pd.read_csv(TABLE)
    report = {f"{s}_{t}": score(tw, s, t) for s in SCORED_SPECS for t in TREATMENTS}
    report["primary"] = "_".join(PRIMARY)
    report["note"] = ("Holdout 2024-2025 scored once with models fit on 2014-2023 "
                      "(no 2020). MAE per team-week in each spec's unit.")
    text = json.dumps(report, indent=2) + "\n"

    if OUT.exists():
        if OUT.read_text() != text:
            raise SystemExit("Holdout numbers differ from the recorded results/holdout.json")
        print("Holdout recomputed; matches the recorded results exactly.")
    else:
        OUT.write_text(text)
        print("Holdout scored and recorded in results/holdout.json")

    for key in (f"{s}_{t}" for s in SCORED_SPECS for t in TREATMENTS):
        r = report[key]
        m = r["mae"]
        sp = {s: round(r["replay"][s]["final_regular"]["spearman"], 2) for s in r["replay"]}
        print(f"[{key}{' PRIMARY' if key == report['primary'] else ''}] MAE baseline "
              f"{m['baseline']:.2f}, linear {m['linear']:.2f}, gbt {m['gbt']:.2f} -> "
              f"{r['chosen_model']}; replay Spearman {sp}; "
              f"{'PASS' if r['pass']['passed'] else 'FAIL'}")


if __name__ == "__main__":
    main()
