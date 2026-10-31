"""Every number used in SUMMARY.md and the LinkedIn post, pulled from the result files with its source.

Nothing here is computed afresh: each value is read from a published result file, so a reader
can trace any claim to the file and key it came from. Writes results/post_numbers.json.
"""

import json
from pathlib import Path

import pandas as pd

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
        out["seasons_positive_of_11"] = int(block["seasons_positive"])
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

    # 2. Why the SEC ranks high: results-only top-25 counts.
    lev = t5["headline_levels"]
    n["top25_teams_per_poll_2014_2025"] = {
        "source": "results/t5_sor.json headline_levels (polls 6 to end of regular season)",
        **{G: {"strength_of_record_top25": r(lev[G]["sor25"]), "ap_top25": r(lev[G]["ap25"])}
           for G in ("SEC", "Big Ten", "Big 12", "Pac-12", "ACC")},
        "sec_minus_acc_strength_of_record_top25": stat(t5["sec_minus_acc_sor_top25"]),
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
        "caveat": t6["caveat"],
    }
    n["early_polls_decomposition_t6"] = {
        "source": "results/t6_early.json decomposition",
        "retention_in_final_top25_by_ap_rank": d["retention_by_ap_rank"],
        **{G: {k: r(v) for k, v in d[G].items()} for G in ("SEC", "Big Ten", "Pac-12", "Big 12", "ACC")},
        "SEC_beyond_expected": stat(d["beyond_tests"]["E_SEC"]),
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
        "SEC_minus_ACC_game_day": {"mean": r(b["sec_minus_acc"]), "ci95": [r(v) for v in b["sec_minus_acc_ci"]]},
        "SEC_final_poll": boot(dd["SEC"], "mean"),
    }
    t2 = pre["T2_schedule_boost_by_week"]
    n["per_game_opponent_gap_t2"] = {
        "source": "results/preseason_tests.json T2_schedule_boost_by_week",
        "unit": "opponent's game-day AP rank points minus its final results rank points, per game",
        **{G: {p: boot(t2[G][p]) for p in ("early (weeks 1-4)", "middle (weeks 5-8)", "late (weeks 9+)")}
           for G in ("SEC", "ACC")},
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
        "SEC": {"games": lp["SEC"]["games"], "mean": r(lp["SEC"]["adjusted_overrating"]),
                "ci95": [r(v) for v in lp["SEC"]["ci"]]},
        "ACC": {"games": lp["ACC"]["games"], "mean": r(lp["ACC"]["adjusted_overrating"]),
                "ci95": [r(v) for v in lp["ACC"]["ci"]]},
    }
    OUT.write_text(json.dumps(n, indent=2) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(n)} blocks)")


if __name__ == "__main__":
    main()
