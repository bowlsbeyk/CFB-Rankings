"""Every number used in SUMMARY.md and the LinkedIn post, pulled from the result files with its source.

Nothing here is computed afresh: each value is read from a published result file, so a reader
can trace any claim to the file and key it came from. Writes results/post_numbers.json.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sor_test import HIST, shares, tstats  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = RES / "post_numbers.json"


def load(name):
    return json.loads((RES / name).read_text())


def r(x, n=2):
    return round(float(x), n)


def stat(block, n=2):
    out = {"mean": r(block["mean"], n), "ci95": [r(v, n) for v in block["ci95_t"]]}
    if "seasons_positive" in block:
        out["seasons_positive"] = int(block["seasons_positive"])
        out["seasons"] = int(block.get("seasons", len(block.get("per_season", [])) or 11))
    if "sign_flip_p" in block:
        out["sign_flip_p"] = r(block["sign_flip_p"], 3)
    return out


def boot(block, key="mean_gap", n=2):
    return {"mean": r(block[key], n), "ci95": [r(v, n) for v in block["ci"]]}


def main():
    t5, t6 = load("t5_sor.json"), load("t6_early.json")
    h5, hyp = load("h5_sensitivity.json"), load("hypothesis.json")
    t3, t4 = load("t3_loop.json"), load("t4_referee.json")
    pre = load("preseason_tests.json")
    sor26 = pd.read_csv(RES / "sor_2026.csv").set_index("team")
    sched = pd.read_csv(RES / "schedule_strength_2026.csv").set_index("team")
    week = int(pd.read_csv(ROOT / "data" / "processed" / "team_weeks.csv", usecols=["season", "week"])
               .query("season == 2026").week.max())
    n = {}

    # 1. Miami 2026.
    m, ms = sor26.loc["Miami"], sched.loc["Miami"]
    n["miami_2026"] = {
        "source": "results/sor_2026.csv, results/schedule_strength_2026.csv",
        "after_week": week, "record": m.record, "ap_rank": int(m.ap_rank),
        "sor_rank": int(m.sor_rank), "sor_rank_range_across_11_settings": [int(m.sor_rank_min), int(m.sor_rank_max)],
        "colley_rank": int(m.colley_rank), "performance_rank": int(m.perf_rank),
        "schedule_rank_by_opponents_game_day_poll": int(ms.poll_rank),
        "schedule_rank_by_opponents_2026_results": int(ms.rating_rank),
        "schedules_ranked": int(len(sched)),
        "opponents_in_ap_top25_on_game_day": "none" if ms.poll_sos == 0 else "some",
        "teams_with_no_ap_top25_opponent_yet": int((sched.poll_sos == 0).sum()),
        "schedule_rank_by_2026_results_among_power_conference_teams": [
            int(sched[sched.conf_group != "Other"].rating_sos.rank(ascending=False)["Miami"]),
            int((sched.conf_group != "Other").sum())],
        "note": "schedule ranks: 1 = toughest; by game-day poll = opponents' AP top-25 points in the poll "
                "before each game (0 outside the top 25); by results = opponents' 2026 season-only rating",
    }
    w = sor26.loc["Wake Forest"]
    n["wake_forest_2026"] = {"source": "results/sor_2026.csv", "record": w.record, "ap_rank": int(w.ap_rank),
                             "sor_rank": int(w.sor_rank)}
    top = sor26.sort_values("sor_rank").head(10)
    n["sor_top10_2026"] = {"source": "results/sor_2026.csv",
                           "teams": [{"team": t, "group": x.group, "record": x.record, "sor_rank": int(x.sor_rank),
                                      "ap_rank": None if pd.isna(x.ap_rank) else int(x.ap_rank)}
                                     for t, x in top.iterrows()]}

    u = sor26.loc["UCLA"]
    n["ucla_2026"] = {"source": "results/sor_2026.csv", "record": u.record, "ap_rank": int(u.ap_rank),
                      "sor_rank": int(u.sor_rank), "sor_rank_range_across_11_settings": [int(u.sor_rank_min), int(u.sor_rank_max)],
                      "colley_rank": int(u.colley_rank)}

    # 2. Why the SEC ranks high: results-only top-25 counts.
    lev = t5["headline_levels"]
    n["top25_teams_per_poll_2014_2025"] = {
        "source": "results/t5_sor.json headline_levels (polls 6 to end of regular season)",
        **{G: {"strength_of_record_top25": r(lev[G]["sor25"]), "ap_top25": r(lev[G]["ap25"])}
           for G in ("SEC", "Big Ten", "Big 12", "Pac-12", "ACC")},
        "sec_minus_acc_strength_of_record_top25": stat(t5["sec_minus_acc_sor_top25"]),
    }
    # SEC minus each other power conference, recomputed from results/sor_weekly.csv the same way as
    # T5's SEC-minus-ACC figure (which it reproduces). Descriptive, added for the summary.
    sw = pd.read_csv(RES / "sor_weekly.csv")
    sw = sw[sw.season.isin(HIST)]
    diffs = {}
    for _, ds in sw.groupby("season"):
        per = {}
        for _, d in ds.groupby("week"):
            sl, _ = shares(d.set_index("team").sor_rank)
            g = d.set_index("team").group
            for G in ("ACC", "Big Ten", "Big 12", "Pac-12"):
                if (g == G).any():
                    per.setdefault(G, []).append(sl[g == "SEC"].sum() - sl[g == G].sum())
        for G, v in per.items():
            diffs.setdefault(G, []).append(float(np.mean(v)))
    n["sec_minus_each_conference_strength_of_record_top25"] = {
        "source": "results/sor_weekly.csv (sor_rank, polls 6 to end of regular season), computed in src/post_numbers.py; "
                  "descriptive, added after results were seen; the ACC row reproduces results/t5_sor.json",
        **{G: stat(tstats(v)) for G, v in diffs.items()},
    }
    n["sec_vs_outsiders_t4"] = {
        "source": "results/t4_referee.json",
        "note": "actual margin (capped at 28) minus margin predicted by the results rating, points per game",
        "all_games": {**boot(t4["SEC"]["all"], "mean_residual"), "games": t4["SEC"]["all"]["games"]},
        "postseason_only": {**boot(t4["SEC"]["postseason_only"], "mean_residual"),
                            "games": t4["SEC"]["postseason_only"]["games"]},
        "vs_power_opponents": {**boot(t4["SEC"]["vs_power_opponents"], "mean_residual"),
                               "games": t4["SEC"]["vs_power_opponents"]["games"]},
        "head_to_head_sec_vs_acc": {k: t4["head_to_head_SEC_vs_ACC"][k] for k in ("games", "sec_wins", "acc_wins")},
        "other_conferences_all_games": {G: {**boot(t4[G]["all"], "mean_residual"), "games": t4[G]["all"]["games"]}
                                        for G in ("ACC", "Big Ten", "Big 12", "Pac-12")},
    }

    # 3. The AP vs strength of record, season-long (T5).
    g = t5["robustness_gate"]
    n["ap_extra_sec_spots_season_long_t5"] = {
        "source": "results/t5_sor.json primary, robustness_gate",
        "E_SEC": stat(t5["primary"]["E_SEC"]), "D_PWR": stat(t5["primary"]["D_PWR"]),
        "D_ACC": stat(t5["primary"]["D_ACC"]),
        "label_part1": t5["label_part1"], "label_part1_robust": g["label_part1_robust"],
        "label_part2": t5["label_part2"], "label_part2_robust": g["label_part2_robust"],
        "E_SEC_with_t4_all_games_calibration": r(g["by_check"]["SOR top25|x1.0|t4_all"]["E_SEC"]),
        "with_t4_all_games_calibration": {q: r(v) for q, v in g["by_check"]["SOR top25|x1.0|t4_all"].items()},
        "with_t4_power_games_calibration": {q: r(v) for q, v in g["by_check"]["SOR top25|x1.0|t4_power"].items()},
        "excess_by_group_mean": {G: r(v["mean"]) for G, v in t5["primary_by_group"].items()},
        "other_power_bloc_excess": stat(tstats(np.subtract(t5["primary"]["E_SEC"]["per_season"],
                                                           t5["primary"]["D_PWR"]["per_season"]))),
        "strength_vs_record_gap_SEC": {
            "note": "simulated top 25 ordered by strength minus top 25 ordered by record, SEC slots per poll "
                    "(the 'noise baseline'); mean over seasons",
            "mean": r(np.mean([v["baseline"]["SEC"] for v in t5["noise_baseline"]["per_season"].values()]))},
        "E_SEC_vs_performance_top25_descriptive": stat(t5["performance_top25_descriptive"]["E_SEC"]),
    }
    bf = t5["week_bands_vs_final_record"]
    n["sec_extra_spots_by_stage_vs_end_of_season_record"] = {
        "source": "results/t6_early.json primary (polls 1-5); results/t5_sor.json week_bands_vs_final_record",
        "polls 1-5": stat(t6["primary"]["E_SEC"]),
        **{b: stat(bf[b]["E_SEC"]) for b in ("polls 6-8", "polls 9-11", "polls 12+", "end of regular season")},
    }

    # 4. Early polls (T6).
    d = t6["decomposition"]
    n["early_polls_t6"] = {
        "source": "results/t6_early.json",
        "E_SEC": stat(t6["primary"]["E_SEC"]), "D_PWR": stat(t6["primary"]["D_PWR"]),
        "D_ACC": stat(t6["primary"]["D_ACC"]),
        "by_group_mean": {G: r(v) for G, v in t6["by_group"].items()},
        "label_part1": t6["label_part1"], "label_part1_robust": t6["robustness_gate"]["label_part1_robust"],
        "E_SEC_sign_holds_in_all_checks": t6["robustness_gate"]["summary"]["E_SEC"]["same_sign_everywhere"],
        "E_SEC_min_across_checks": r(t6["robustness_gate"]["summary"]["E_SEC"]["min_slots"]),
        "E_SEC_vs_final_performance_top25": r(t6["robustness_gate"]["by_check"]["final performance top 25"]["E_SEC"]),
        "with_t4_all_games_calibration": {q: r(v) for q, v in
                                          t6["robustness_gate"]["by_check"]["SOR top25|x1.0|t4_all"].items()},
        "other_power_bloc_excess": stat(tstats(np.subtract(t6["primary"]["E_SEC"]["per_season"],
                                                           t6["primary"]["D_PWR"]["per_season"]))),
        "caveat": t6["caveat"],
    }
    n["early_polls_decomposition_t6"] = {
        "source": "results/t6_early.json decomposition",
        "retention_in_final_top25_by_ap_rank": d["retention_by_ap_rank"],
        **{G: {k: r(v) for k, v in d[G].items()} for G in ("SEC", "Big Ten", "Pac-12", "Big 12", "ACC")},
        "SEC_beyond_expected": stat(d["beyond_tests"]["E_SEC"]),
        "SEC_share_missing_final_top25": r((d["SEC"]["expected"] + d["SEC"]["beyond"]) / d["SEC"]["a"], 3),
        "SEC_share_expected_to_miss": r(d["SEC"]["expected"] / d["SEC"]["a"], 3),
        "note": "descriptive breakdown added after results were seen (DEVIATIONS.md, audit corrections item 4b)",
    }
    ps = t6["preseason_shortfall_vs_SOR"]
    n["preseason_ranked_teams_vs_final_record_t6"] = {
        "source": "results/t6_early.json preseason_shortfall_vs_SOR",
        "A_SEC_ranks": stat(ps["A_SEC"]), "reading": ps["reading_hyped"],
        "share_finishing_outside_final_top25": ps["by_group_share_outside_final_SOR_top25"],
    }

    # 5. Game-day rankings and schedules (earlier tests, corrected versions).
    b = h5["final_poll_corrected"]["B"]
    dd = h5["final_poll_corrected"]["D"]
    n["schedule_look_game_day_vs_final_results"] = {
        "source": "results/h5_sensitivity.json final_poll_corrected B (game-day poll) and D (final poll)",
        "unit": "schedule-rank places of ~130, top-25 rank-point scale on both sides",
        "SEC_game_day": boot(b["SEC"], "mean"), "ACC_game_day": boot(b["ACC"], "mean"),
        "Big_12_game_day": boot(b["Big 12"], "mean"), "Big_Ten_game_day": boot(b["Big Ten"], "mean"),
        "SEC_minus_ACC_game_day": {"mean": r(b["sec_minus_acc"]), "ci95": [r(v) for v in b["sec_minus_acc_ci"]]},
        "SEC_final_poll": boot(dd["SEC"], "mean"),
    }
    t2 = pre["T2_schedule_boost_by_week"]
    n["per_game_opponent_gap_t2"] = {
        "source": "results/preseason_tests.json T2_schedule_boost_by_week",
        "unit": "opponent's game-day AP rank points minus its final results rank points, per game",
        **{G: {**{p: boot(t2[G][p]) for p in ("early (weeks 1-4)", "middle (weeks 5-8)", "late (weeks 9+)")},
               "early_minus_late": {"mean": r(t2[G]["early_minus_late"]),
                                    "ci95": [r(v) for v in t2[G]["early_minus_late_ci"]]}}
           for G in ("SEC", "ACC")},
        "SEC_minus_ACC": {p: {"mean": r(t2["sec_minus_acc"][p]["diff"]), "ci95": [r(v) for v in t2["sec_minus_acc"][p]["ci"]]}
                          for p in ("early (weeks 1-4)", "middle (weeks 5-8)", "late (weeks 9+)")},
    }
    sr = hyp["season_rating"]["poll_vs_rating"]
    n["poll_rank_above_results_rank"] = {
        "source": "results/hypothesis.json season_rating.poll_vs_rating (polls 6+, places)",
        **{G: boot(sr[G]) for G in ("SEC", "Big 12", "ACC", "Big Ten")},
        "SEC_minus_ACC": {"mean": r(sr["sec_minus_acc"]), "ci95": [r(v) for v in sr["sec_minus_acc_ci"]]},
    }
    lp = t3["primary_lost_to_ranked_same_conference"]
    n["ranked_loop_t3"] = {
        "source": "results/t3_loop.json primary_lost_to_ranked_same_conference",
        "note": "places a team is ranked above where its season ends up, after losing to a ranked same-conference team",
        **{G: {"games": lp[G]["games"], "beyond_typical_for_pre_game_rank": r(lp[G]["adjusted_overrating"]),
               "ci95": [r(v) for v in lp[G]["ci"]], "before_adjustment": r(lp[G]["raw_overrating"])}
           for G in ("SEC", "ACC")},
    }
    cal = load("calibration_check.json")
    n["calibration_check_schedules_and_poll_places"] = {
        "source": "results/calibration_check.json (descriptive, added before publication; DEVIATIONS.md 2026-10-31)",
        **{v: {"SEC_game_day_schedule_places": cal[v]["h5_variant_B_schedule_places"]["SEC"],
               "ACC_game_day_schedule_places": cal[v]["h5_variant_B_schedule_places"]["ACC"],
               "SEC_minus_ACC_game_day_schedule_places": cal[v]["h5_variant_B_schedule_places"]["SEC_minus_ACC"],
               "SEC_per_game": cal[v]["t2_per_game_rank_points"]["SEC"],
               "SEC_minus_ACC_per_game": cal[v]["t2_per_game_rank_points"]["SEC_minus_ACC"],
               "SEC_poll_places_above_rating": cal[v]["poll_places_above_season_rating"]["SEC"],
               "ACC_poll_places_above_rating": cal[v]["poll_places_above_season_rating"]["ACC"]}
           for v in ("uncalibrated", "t4_all", "t4_power")},
        "pac12_game_day_schedule_places_2014_2023": cal["h5_variant_B_with_pac12_split"]["Pac-12"],
        "ACC_vs_power_opponents_t4": boot(t4["ACC"]["vs_power_opponents"], "mean_residual"),
    }
    OUT.write_text(json.dumps(n, indent=2) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(n)} blocks)")


if __name__ == "__main__":
    main()
