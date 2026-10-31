"""Calibration check of the schedule and poll-place results (descriptive, added before publication).

T5 and T6 were checked against two calibrations of the results rating: each power conference's
performance rating shifted by its average T4 residual against outsiders (all games, or power-
conference opponents only). The schedule checks (H5 variant B, T2) and the poll-place gap (H2 on
the season-only rating) were never put through the same calibrations. This script reruns them,
unchanged, on the calibrated rating. With zero offsets it reproduces the published numbers.

It also splits the Pac-12 (2014-2023) out of "Other" in H5 variant B.

Writes results/calibration_check.json. Logged in DEVIATIONS.md (2026-10-31, calibration check).
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bias_tests as bt  # noqa: E402
import h5_sensitivity as h5  # noqa: E402
import hypothesis as hy  # noqa: E402
import preseason_tests as pt  # noqa: E402
from sor_test import group_of, offsets_from_t4  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "calibration_check.json"
FCS = h5.FCS


def r2(x):
    return round(float(x), 2)


def recalibrate(ratings, conf, offsets):
    """Add each team's conference offset to its performance rating, then rebuild the 50/50
    combined rating and its rank exactly as src/season_rating.py does."""
    r = ratings.copy()
    grp = [group_of(conf.get((s, t), "FCS"), t, s) for s, t in zip(r.season, r.team)]
    off = np.array([offsets.get(g, 0.0) for g in grp])
    fbs = (r.team != FCS).to_numpy()
    r.loc[fbs, "performance_rating"] = r.loc[fbs, "performance_rating"].to_numpy() + off[fbs]
    out = []
    for _, d in r.groupby(["season", "week"], sort=False):
        f = d.team != FCS
        res, perf = d.results_rating, d.performance_rating
        comb = 0.5 * (res - res[f].mean()) / res[f].std() + 0.5 * (perf - perf[f].mean()) / perf[f].std()
        d = d.assign(combined=comb)
        d["strength_rank"] = comb[f].rank(ascending=False, method="min").reindex(d.index)
        out.append(d)
    return pd.concat(out).loc[r.index]


def h5_b(tw, ratings):
    s = h5.schedules(tw, ratings, "corrected")
    m = bt.group_means(s, "inflation_B", np.random.default_rng(0))
    return {**{c: {"mean": r2(m[c]["mean"]), "ci95": [r2(v) for v in m[c]["ci"]]} for c in bt.CONFS},
            "SEC_minus_ACC": {"mean": r2(m["sec_minus_acc"]), "ci95": [r2(v) for v in m["sec_minus_acc_ci"]]}}


def t2_gaps(ratings):
    tw = pd.read_csv(pt.TABLE)
    tw = tw[tw.season.isin(pt.SEASONS)]
    t = pt.t2(tw, ratings, np.random.default_rng(0))
    return {"SEC_minus_ACC": {b: {"mean": r2(v["diff"]), "ci95": [r2(x) for x in v["ci"]]}
                              for b, v in t["sec_minus_acc"].items()},
            "SEC": {b: {"mean": r2(t["SEC"][b]["mean_gap"]), "ci95": [r2(x) for x in t["SEC"][b]["ci"]]}
                    for b in pt.BANDS}}


def poll_places(ratings):
    tw0 = pd.read_csv(hy.TABLE)
    tw = hy.with_elo(tw0)
    tw = tw[tw.season.isin(hy.SEASONS)]
    tws = tw.merge(ratings[["season", "week", "team", "combined"]].rename(columns={"combined": "season_rating"}),
                   on=["season", "week", "team"], how="left")
    o = hy.poll_vs_elo(tws, np.random.default_rng(0), "season_rating", 5)
    return {**{g: {"mean": r2(o[g]["mean_gap"]), "ci95": [r2(x) for x in o[g]["ci"]]}
               for g in ("SEC", "ACC", "Big Ten", "Big 12")},
            "SEC_minus_ACC": {"mean": r2(o["sec_minus_acc"]), "ci95": [r2(x) for x in o["sec_minus_acc_ci"]]}}


def main():
    tw = pd.read_csv(h5.TABLE)
    ratings = pd.read_csv(h5.RATINGS)
    conf = tw.groupby(["season", "team"]).conference.first().to_dict()
    offsets = offsets_from_t4()
    variants = {"uncalibrated": {}, "t4_all": offsets["t4_all"], "t4_power": offsets["t4_power"]}
    report = {"note": "Descriptive check added before publication, after all results were seen. The same "
                      "code as H5 variant B, T2 and H2 (season-only rating), rerun on the results rating "
                      "calibrated with T4 offsets. 'uncalibrated' reproduces the published numbers.",
              "offsets": offsets}
    for name, off in variants.items():
        rr = recalibrate(ratings, conf, off) if off else ratings
        report[name] = {"h5_variant_B_schedule_places": h5_b(tw, rr),
                        "t2_per_game_rank_points": t2_gaps(rr),
                        "poll_places_above_season_rating": poll_places(rr)}
        print(name, json.dumps(report[name]["h5_variant_B_schedule_places"]["SEC"]),
              json.dumps(report[name]["t2_per_game_rank_points"]["SEC_minus_ACC"]))

    # Pac-12 split out of "Other" in H5 variant B (uncalibrated, 2014-2023).
    s = h5.schedules(tw, ratings, "corrected")
    s["conf_group"] = [("Pac-12" if conf.get((a, b)) == "Pac-12" and a <= 2023 else g)
                       for a, b, g in zip(s.season, s.team, s.conf_group)]
    saved = bt.CONFS
    bt.CONFS = ["SEC", "ACC", "Big Ten", "Big 12", "Pac-12", "Other"]
    m = bt.group_means(s, "inflation_B", np.random.default_rng(0))
    bt.CONFS = saved
    report["h5_variant_B_with_pac12_split"] = {
        c: {"mean": r2(m[c]["mean"]), "ci95": [r2(v) for v in m[c]["ci"]], "team_seasons": int(m[c]["team_seasons"])}
        for c in ("SEC", "ACC", "Big Ten", "Big 12", "Pac-12", "Other")}
    print("pac12 split", json.dumps(report["h5_variant_B_with_pac12_split"]["Pac-12"]))
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
