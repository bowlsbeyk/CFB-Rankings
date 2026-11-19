"""Tables for the shareable data page, all read from results/post_numbers.json.

Writes results/page/*.csv. Nothing is computed here beyond reshaping.
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = RES / "page"
POWER = ["SEC", "Pac-12", "Big Ten", "Big 12", "ACC"]


def row(label, x, **extra):
    ci = x.get("ci95") or [None, None]
    return {"label": label, "value": x["mean"], "lo": ci[0], "hi": ci[1],
            "seasons_positive": x.get("seasons_positive"), "seasons": x.get("seasons"), **extra}


def main():
    n = json.loads((RES / "post_numbers.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    t8, t10, em = (n["same_resume_different_conference_t8"], n["epa_yardstick_t10"],
                   n["season_end_matched_on_espn_sor"])

    pd.DataFrame([row(g, t8["posthoc_placebo_by_focal_conference"][g]) for g in POWER]) \
        .rename(columns={"label": "conference"}).to_csv(OUT / "premium_by_conference.csv", index=False)

    h = n["head_start_by_conference"]
    rows = []
    for g in POWER:
        for key, lab in (("started_higher", "Started ahead"), ("started_level", "Started level"),
                         ("started_lower", "Started behind")):
            rows.append({"conference": g, "start": lab, **{k: v for k, v in row(lab, h[g][key]).items() if k != "label"},
                         "share_started_ahead": h[g]["share_started_ahead"]})
    pd.DataFrame(rows).to_csv(OUT / "head_start.csv", index=False)

    rob = [row("Main test (logged in advance)", t8["M_SEC"]),
           row("Scoring margin also matched (post hoc)", t8["posthoc_margin_held_fixed"]),
           {"label": "Calibrated: all outside games", "value": t8["checks"]["SOR, T4 all-games calibration"]},
           {"label": "Calibrated: power-conference games", "value": t8["checks"]["SOR, T4 power-games calibration"]},
           row("Playoff committee instead of AP", t8["M_CFP_committee"]),
           row("Matched on EPA per play instead", t10["match_on_EPA_instead"]),
           row("EPA per play also matched (logged)", t10["M_SEC_EPA_held_fixed"]),
           row("Allowing for how the season ended (post hoc)", n["verification_checks_t8"]["SEC"]["allowing_for_how_season_ended"]),
           row("Preseason gap held fixed (post hoc)", n["verification_checks_t8"]["SEC"]["preseason_gap_held_fixed"]),
           row("Last regular-season poll, ours (post hoc)", n["verification_checks_t8"]["SEC"]["last_regular_season_week_our_yardstick"]),
           row("Final poll, on ESPN's résumé rank (post hoc)", em["SEC"])]
    pd.DataFrame(rob).rename(columns={"label": "check"}).to_csv(OUT / "premium_robustness.csv", index=False)

    v = n["verification_checks_t8"]
    pd.DataFrame([row(m, v["SEC_by_match_conference"][m]) for m in ("ACC", "Big Ten", "Big 12", "Pac-12")]) \
        .rename(columns={"label": "opponent_conference"}).to_csv(OUT / "sec_by_opponent.csv", index=False)
    pd.DataFrame([{"conference": g, **{k: v[g][k]["mean"] for k in ("allowing_for_how_season_ended", "preseason_gap_held_fixed")},
                   "main_test": t8["posthoc_placebo_by_focal_conference"][g]["mean"]} for g in POWER]) \
        .to_csv(OUT / "adjusted_by_conference.csv", index=False)
    st = t8["posthoc_by_stage"]
    pd.DataFrame([row(k.replace("polls", "Polls"), st[k]) for k in ("polls 6-8", "polls 9-11", "polls 12+")]) \
        .rename(columns={"label": "stage"}).to_csv(OUT / "premium_by_stage.csv", index=False)

    lv = n["top25_teams_per_poll_2014_2025"]
    pd.DataFrame([{"conference": g, "strength_of_record_top25": lv[g]["strength_of_record_top25"],
                   "ap_top25": lv[g]["ap_top25"]} for g in ["SEC", "Big Ten", "Big 12", "Pac-12", "ACC"]]) \
        .to_csv(OUT / "top25_per_poll.csv", index=False)

    e = n["external_cross_check_t9"]
    pd.DataFrame([{"conference": g, "vs_espn_sor": e["our_SOR_vs_ESPN_SOR"]["lean_by_group"][g],
                   "vs_sp_plus": e["our_margin_vs_SP+"]["lean_by_group"][g]} for g in POWER]) \
        .to_csv(OUT / "ours_vs_espn_spplus.csv", index=False)

    m = n["miami_2026"]
    pd.DataFrame([
        {"measure": "AP poll", "rank": m["ap_rank"]},
        {"measure": "Strength of record", "rank": m["sor_rank"]},
        {"measure": "Wins and losses (schedule-adjusted)", "rank": m["colley_rank"]},
        {"measure": "Scoring margin (schedule-adjusted)", "rank": m["performance_rank"]},
        {"measure": "Schedule, by opponents' results", "rank": m["schedule_rank_by_opponents_2026_results"]},
        {"measure": "Schedule, by opponents' game-day AP rank", "rank": m["schedule_rank_by_opponents_game_day_poll"]},
    ]).assign(after_week=m["after_week"], record=m["record"], out_of=m["schedules_ranked"]) \
        .to_csv(OUT / "miami_2026.csv", index=False)
    print(f"Wrote {len(list(OUT.glob('*.csv')))} tables to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
