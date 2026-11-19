"""Eight square images for the LinkedIn post (01_miami_schedule.png ... 08_vs_espn_spplus.png), drawn from
results/post_numbers.json.

Writes results/figures/linkedin/01_miami_schedule.png ... 04_schedule_boost.png (1200 x 1200).
Every value is read from a result file; nothing is computed here.
"""

import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = RES / "figures" / "linkedin"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e4e3df"
HIGHLIGHT = "#2a78d6"   # categorical slot 1 (blue)
SECOND = "#eb6834"      # categorical slot 2 (orange)
OTHER = "#b9b8b2"       # neutral for non-highlighted groups
FOOT = ("Data: CollegeFootballData.com, cfbfastR. AP polls 2014–2025 (no 2020). "
        "Code and every number: github.com/bowlsbeyk/CFB-Rankings")

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
})


def frame(title, subtitle, foot=None):
    fig = plt.figure(figsize=(6, 6), dpi=200)
    t = textwrap.fill(title, 40)
    st = textwrap.fill(subtitle, 76)
    fig.text(0.06, 0.95, t, fontsize=16, fontweight="bold", color=INK, va="top", linespacing=1.15)
    y = 0.95 - 0.052 * (t.count("\n") + 1) - 0.012
    fig.text(0.06, y, st, fontsize=9.5, color=INK2, va="top", linespacing=1.3)
    fig.text(0.06, 0.03, textwrap.fill(foot or FOOT, 110), fontsize=6.5, color=MUTED, va="bottom")
    return fig


def note(fig, text):
    fig.text(0.06, 0.085, textwrap.fill(text, 88), fontsize=8.5, color=INK2, va="bottom", linespacing=1.3)


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, facecolor=SURFACE)
    plt.close(fig)
    print(f"Wrote {(OUT / name).relative_to(ROOT)}")


def miami(n):
    import pandas as pd
    m = n["miami_2026"]
    total = m["schedules_ranked"]
    d = pd.read_csv(RES / "sor_2026.csv").set_index("team")

    def leader(col):
        t = d[col].idxmin()
        return f"{t}, {d.loc[t, 'record']}"

    def ordinal(k):
        k = int(k)
        return f"{k}{'th' if 10 <= k % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(k % 10, 'th')}"

    ranks = [int(m["sor_rank"]), int(m["colley_rank"]), int(m["performance_rank"])]
    lo, hi = m["sor_rank_range_across_11_settings"]
    fig = frame(f"Miami on performance alone: top {max(ranks)} on every measure",
                f"2026 after week {m['after_week']}. Every ranking uses only this season's scores and schedules "
                "(no polls, no preseason, no names) and adjusts for who each team has played.",
                foot=f"Data: CollegeFootballData.com, cfbfastR. 2026 through week {m['after_week']}. "
                     "Code and every number: github.com/bowlsbeyk/CFB-Rankings")
    rows = [
        ("Strength of record", f"How hard would {m['record']} against this exact schedule be?", ranks[0],
         f"Between #{lo} and #{hi} across all 11 versions; #1: {leader('sor_rank')}"),
        ("Wins and losses, schedule-adjusted", "Colley ranking", ranks[1], f"#1: {leader('colley_rank')}"),
        ("Scoring margin, schedule-adjusted", "Margin capped at 28 points", ranks[2], f"#1: {leader('perf_rank')}"),
    ]
    top = 0.655
    for i, (name, sub, rank, note_) in enumerate(rows):
        y = top - i * 0.125
        fig.text(0.06, y, f"#{rank}", fontsize=34, fontweight="bold", color=HIGHLIGHT, va="center")
        fig.text(0.27, y + 0.025, name, fontsize=13, fontweight="bold", color=INK, va="center")
        fig.text(0.27, y - 0.012, sub, fontsize=9.5, color=INK2, va="center")
        fig.text(0.27, y - 0.042, note_, fontsize=9.5, color=INK2, va="center")
    fig.add_artist(plt.Line2D([0.06, 0.94], [0.315, 0.315], color=GRID, lw=1))
    r = m["schedule_rank_by_opponents_2026_results"]
    pw = m["schedule_rank_by_2026_results_among_power_conference_teams"]
    fig.text(0.06, 0.29, "The schedule, for context", fontsize=11, fontweight="bold", color=INK, va="top")
    fig.text(0.06, 0.255, textwrap.fill(
        f"By how its opponents have actually played, Miami's schedule is {ordinal(r)} toughest of {total} "
        f"({ordinal(pw[0])} of {pw[1]} power-conference teams). The rankings above already account for it: "
        "a tougher schedule makes the same record more impressive, a softer one less.", 82),
        fontsize=8.8, color=INK2, va="top", linespacing=1.35)
    if m["opponents_in_ap_top25_on_game_day"] == "none":
        tail = (f"Counted by opponents' AP rank on game day instead, Miami has faced no ranked team, like "
                f"{m['teams_with_no_ap_top25_opponent_yet'] - 1} other teams.")
    else:
        tail = (f"Counted by opponents' AP rank on game day instead, its schedule is "
                f"{ordinal(m['schedule_rank_by_opponents_game_day_poll'])} of {total}.")
    note(fig, tail)
    save(fig, "01_miami_schedule.png")


def levels(n):
    lv = n["top25_teams_per_poll_2014_2025"]
    groups = ["SEC", "Big Ten", "Big 12", "Pac-12", "ACC"]
    fig = frame("By results alone, the SEC still has the most top-25 teams",
                "Teams per poll in the top 25, poll 6 to season's end. Strength of record uses only "
                "scores and schedules: no polls, no preseason, no names.")
    ax = fig.add_axes([0.16, 0.2, 0.78, 0.5])
    y = list(range(len(groups)))[::-1]
    h = 0.36
    sor = [lv[g]["strength_of_record_top25"] for g in groups]
    ap = [lv[g]["ap_top25"] for g in groups]
    ax.barh([v + h / 2 + 0.02 for v in y], sor, height=h, color=HIGHLIGHT, label="Strength of record (results only)")
    ax.barh([v - h / 2 - 0.02 for v in y], ap, height=h, color=OTHER, label="AP poll")
    for yy, s, a in zip(y, sor, ap):
        ax.text(s + 0.08, yy + h / 2 + 0.02, f"{s:.1f}", va="center", fontsize=11, color=INK)
        ax.text(a + 0.08, yy - h / 2 - 0.02, f"{a:.1f}", va="center", fontsize=11, color=INK2)
    ax.set_yticks(y)
    ax.set_yticklabels(groups, fontsize=11)
    ax.set_xlim(0, 7.2)
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.legend(loc="upper right", frameon=False, fontsize=9, bbox_to_anchor=(1.0, 1.08), ncol=2)
    d = n["sec_minus_each_conference_strength_of_record_top25"]
    note(fig, f"SEC lead by record: clear over the ACC (+{d['ACC']['mean']:.1f}), not clear over the "
             f"Big Ten (+{d['Big Ten']['mean']:.1f}, 95% CI {d['Big Ten']['ci95'][0]:+.1f} to {d['Big Ten']['ci95'][1]:+.1f}). "
             "Pac-12 2014–2023 only.")
    save(fig, "02_top25_by_results.png")


def stages(n):
    st = n["sec_extra_spots_by_stage_vs_end_of_season_record"]
    keys = ["polls 1-5", "polls 6-8", "polls 9-11", "polls 12+", "end of regular season"]
    labels = ["Polls\n1–5", "Polls\n6–8", "Polls\n9–11", "Polls\n12+", "Final reg.\nseason poll"]
    fig = frame("Early polls list extra SEC teams. The gap fades.",
                "SEC teams per AP top 25 beyond the end-of-season strength-of-record top 25, "
                "with 95% confidence intervals. 2014–2025 seasons (no 2020).")
    ax = fig.add_axes([0.14, 0.25, 0.8, 0.5])
    x = list(range(len(keys)))
    m = [st[k]["mean"] for k in keys]
    lo = [st[k]["mean"] - st[k]["ci95"][0] for k in keys]
    hi = [st[k]["ci95"][1] - st[k]["mean"] for k in keys]
    ax.axhline(0, color=INK2, lw=1)
    ax.errorbar(x, m, yerr=[lo, hi], fmt="none", ecolor=HIGHLIGHT, elinewidth=2, capsize=0, alpha=0.45)
    ax.plot(x, m, color=HIGHLIGHT, lw=2)
    ax.scatter(x, m, s=110, color=HIGHLIGHT, edgecolor=SURFACE, linewidth=2, zorder=3)
    for xx, v in zip(x, m):
        ax.text(xx + 0.1, v + 0.12, f"{v:+.2f}", va="bottom", fontsize=10, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylabel("Extra SEC teams per poll", fontsize=9.5)
    ax.yaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.set_xlim(-0.4, len(keys) - 0.4)
    e = n["early_polls_t6"]
    note(fig, f"Hindsight, not proof of intent. Other power conferences are over-listed early too "
             f"(average +{e['other_power_bloc_excess']['mean']:.2f} per conference); the SEC's lead over them "
             "is not statistically clear.")
    save(fig, "03_early_polls_fade.png")


def schedules(n):
    c = n["calibration_check_schedules_and_poll_places"]
    s = n["schedule_look_game_day_vs_final_results"]
    rows = [("SEC", s["SEC_game_day"]), ("Pac-12*", c["pac12_game_day_schedule_places_2014_2023"]),
            ("Big 12", s["Big_12_game_day"]), ("ACC", s["ACC_game_day"]), ("Big Ten", s["Big_Ten_game_day"])]
    fig = frame("Game-day rankings make SEC schedules look tougher",
                "Places a schedule moves up (of ~130) when opponents are judged by their AP rank on game day "
                "instead of by their final results, with 95% confidence intervals.")
    ax = fig.add_axes([0.16, 0.27, 0.78, 0.44])
    y = list(range(len(rows)))[::-1]
    for yy, (g, v) in zip(y, rows):
        col = HIGHLIGHT if g == "SEC" else OTHER
        ax.plot(v["ci95"], [yy, yy], color=col, lw=2, alpha=0.6, solid_capstyle="round")
        ax.scatter([v["mean"]], [yy], s=140, color=col, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.text(v["ci95"][1] + 0.5, yy, f"{v['mean']:+.2f}", va="center", fontsize=10, color=INK)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels([g for g, _ in rows], fontsize=11)
    ax.set_xlim(-10, 13.5)
    ax.set_xlabel("← looks easier on game day     looks tougher on game day →", fontsize=9)
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    lo, hi = c["t4_all"]["SEC_game_day_schedule_places"]["mean"], c["t4_power"]["SEC_game_day_schedule_places"]["mean"]
    note(fig, f"*Pac-12 2014–2023. The SEC's boost holds all season and keeps its sign when the rating is "
             f"recalibrated ({lo:+.1f}, not statistically clear, to {hi:+.1f}); whether it beats the ACC's depends on that "
             "calibration.")
    save(fig, "04_schedule_boost.png")


def same_resume(n):
    t = n["same_resume_different_conference_t8"]
    pl = t["posthoc_placebo_by_focal_conference"]
    rows = [("SEC", pl["SEC"]), ("Pac-12*", pl["Pac-12"]), ("Big Ten", pl["Big Ten"]),
            ("Big 12", pl["Big 12"]), ("ACC", pl["ACC"])]
    fig = frame("Same record so far, different conference: who gets ranked higher",
                "AP poll places a team sits above a team from another power conference with the same number "
                "of losses and nearly the same strength of record. Polls 6+, 2014–2025, 95% intervals.")
    ax = fig.add_axes([0.16, 0.27, 0.78, 0.44])
    y = list(range(len(rows)))[::-1]
    for yy, (g, v) in zip(y, rows):
        col = HIGHLIGHT if g == "SEC" else (SECOND if g == "ACC" else OTHER)
        ax.plot(v["ci95"], [yy, yy], color=col, lw=2, alpha=0.6, solid_capstyle="round")
        ax.scatter([v["mean"]], [yy], s=140, color=col, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.text(max(v["ci95"][1], 0) + 0.25, yy, f"{v['mean']:+.1f}", va="center", fontsize=10, color=INK)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels([g for g, _ in rows], fontsize=11)
    ax.set_xlim(-5, 5.5)
    ax.set_xlabel("← ranked lower than the same résumé     ranked higher →", fontsize=9)
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    m = t["posthoc_margin_held_fixed"]["mean"]
    hi, lo = t["posthoc_sec_preseason_ranked_higher"]["mean"], t["posthoc_sec_preseason_not_higher"]["mean"]
    v = n["verification_checks_t8"]
    note(fig, f"*Pac-12 2014–2023. Main test logged in advance; the other conferences' rows are a post hoc placebo. "
         f"With scoring margin matched too: +{m:.1f}. Part is voters anticipating real quality: allowing for how the "
         f"season ended, SEC +{v['SEC']['allowing_for_how_season_ended']['mean']:.1f}, ACC "
         f"{v['ACC']['allowing_for_how_season_ended']['mean']:.1f}. Committee rankings: +{t['M_CFP_committee']['mean']:.1f}.")
    save(fig, "05_same_resume.png")


def head_start(n):
    h = n["head_start_by_conference"]
    groups = ["SEC", "Pac-12", "Big Ten", "Big 12", "ACC"]
    cols = [("started_higher", "Started ahead", HIGHLIGHT), ("started_level", "Started level", OTHER),
            ("started_lower", "Started behind", SECOND)]
    fig = frame("Preseason head starts stick, and the SEC gets the most of them",
                "AP places above a team from another power conference with the same losses and nearly the "
                "same strength of record, split by who was ranked higher in the preseason poll. 2014–2025, 95% intervals.")
    ax = fig.add_axes([0.16, 0.24, 0.78, 0.44])
    y = list(range(len(groups)))[::-1]
    off = {"started_higher": 0.22, "started_level": 0.0, "started_lower": -0.22}
    for key, lab, col in cols:
        for yy, g in zip(y, groups):
            v = h[g][key]
            ax.plot(v["ci95"], [yy + off[key]] * 2, color=col, lw=1.6, alpha=0.5)
            ax.scatter([v["mean"]], [yy + off[key]], s=70, color=col, edgecolor=SURFACE, linewidth=1.5, zorder=3,
                       label=lab if g == "SEC" else None)
    for yy, g in zip(y, groups):
        ax.text(9.6, yy, f"{h[g]['share_started_ahead']:.0%}", va="center", ha="right", fontsize=10, color=INK)
    ax.text(9.6, len(groups) - 0.55, "how often\nit started\nahead", va="bottom", ha="right", fontsize=7.5, color=INK2)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels(groups, fontsize=11)
    ax.set_xlim(-9, 10)
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.legend(loc="lower left", frameon=False, fontsize=8.5, ncol=3, bbox_to_anchor=(0.0, 1.01))
    v = n["verification_checks_t8"]
    note(fig, "Post hoc and descriptive; small groups, no test of differences. Preseason calls were largely borne out "
         "on the field, so a head start is partly earned. Holding the preseason gap fixed, the SEC still sits "
         f"+{v['SEC']['preseason_gap_held_fixed']['mean']:.1f} places higher and the ACC "
         f"{v['ACC']['preseason_gap_held_fixed']['mean']:.1f}. Pac-12 2014–2023.")
    save(fig, "06_head_start.png")


def robustness(n):
    t8, t10, em = (n["same_resume_different_conference_t8"], n["epa_yardstick_t10"],
                   n["season_end_matched_on_espn_sor"])
    rows = [("Main test (logged in advance)", t8["M_SEC"]),
            ("Scoring margin also matched (post hoc)", t8["posthoc_margin_held_fixed"]),
            ("Calibrated: all outside games", {"mean": t8["checks"]["SOR, T4 all-games calibration"], "ci95": None}),
            ("Calibrated: power-conference games", {"mean": t8["checks"]["SOR, T4 power-games calibration"], "ci95": None}),
            ("Playoff committee instead of AP", t8["M_CFP_committee"]),
            ("Matched on EPA per play instead", t10["match_on_EPA_instead"]),
            ("EPA per play also matched (logged)", t10["M_SEC_EPA_held_fixed"]),
            ("Allowing for how the season ended (post hoc)", n["verification_checks_t8"]["SEC"]["allowing_for_how_season_ended"]),
            ("Preseason gap held fixed (post hoc)", n["verification_checks_t8"]["SEC"]["preseason_gap_held_fixed"]),
            ("Last regular-season poll, ours (post hoc)", n["verification_checks_t8"]["SEC"]["last_regular_season_week_our_yardstick"]),
            ("Final poll, on ESPN's résumé rank (post hoc)", em["SEC"])]
    fig = frame("How sturdy is the SEC premium?",
                "AP places an SEC team sits above a team from another power conference with the same record so far, "
                "under the main checks. 2014–2025, 95% intervals where computed.")
    ax = fig.add_axes([0.47, 0.25, 0.47, 0.49])
    y = list(range(len(rows)))[::-1]
    for yy, (lab, v) in zip(y, rows):
        col = HIGHLIGHT if (v.get("ci95") is None or v["ci95"][0] > 0) and v.get("reading") != "INCONCLUSIVE" else OTHER
        if v.get("ci95"):
            ax.plot(v["ci95"], [yy, yy], color=col, lw=2, alpha=0.55)
        ax.scatter([v["mean"]], [yy], s=110, color=col, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.text(5.6, yy, f"{v['mean']:+.1f}", va="center", ha="right", fontsize=10, color=INK)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels([lab for lab, _ in rows], fontsize=8.5)
    ax.set_xlim(-2.5, 5.8)
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    note(fig, "Blue: interval above zero (calibrations report the estimate only). In-season it stays near +2 under "
         "every check; with EPA also matched it is +1.9 but positive in only 8 of 11 seasons (9 pre-set): "
         "inconclusive. In the last polls of the season there are too few pairs to tell, on ESPN's yardstick or ours.")
    save(fig, "07_premium_robustness.png")


def external(n):
    e = n["external_cross_check_t9"]
    groups = ["SEC", "Big 12", "Big Ten", "Pac-12", "ACC"]
    fig = frame("Our ratings agree with ESPN and SP+, but are tougher on the SEC",
                "Average rank difference, ours minus theirs, for teams in the external top 40, 2014–2025. "
                "Positive = our results-only ratings rank the conference's teams lower.")
    ax = fig.add_axes([0.16, 0.25, 0.78, 0.46])
    y = list(range(len(groups)))[::-1]
    h = 0.34
    a = [e["our_SOR_vs_ESPN_SOR"]["lean_by_group"][g] for g in groups]
    b = [e["our_margin_vs_SP+"]["lean_by_group"][g] for g in groups]
    ax.barh([v + h / 2 + 0.02 for v in y], a, height=h, color=HIGHLIGHT, label="Our strength of record vs ESPN's")
    ax.barh([v - h / 2 - 0.02 for v in y], b, height=h, color=OTHER, label="Our margin rating vs SP+")
    for yy, x1, x2 in zip(y, a, b):
        ax.text(x1 + 0.15, yy + h / 2 + 0.02, f"{x1:+.1f}", va="center", fontsize=9.5, color=INK)
        ax.text(x2 + 0.15, yy - h / 2 - 0.02, f"{x2:+.1f}", va="center", fontsize=9.5, color=INK2)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels(groups, fontsize=11)
    ax.set_xlim(-1, 9.5)
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    r1, r2 = e["our_SOR_vs_ESPN_SOR"]["spearman_mean"], e["our_margin_vs_SP+"]["spearman_mean"]
    note(fig, f"Overall agreement is high (rank correlation {r1:.2f} with ESPN's strength of record, {r2:.2f} with SP+). "
         "Theirs are final values after bowls; ours end with the regular season. Either ours undervalues SEC teams "
         "or theirs credits them with something results alone do not show.")
    save(fig, "08_vs_espn_spplus.png")


def postseason(n):
    ps, era = n["postseason_by_conference"], n["era_before_and_since_nil"]
    groups = ["SEC", "Big Ten", "Big 12", "ACC"]
    fig = frame("Since NIL, the SEC's postseason edge is gone. Its poll credit didn't shrink.",
                "Bowl and playoff win share by conference, FBS opponents only: 2014–2019 against 2021–2025, the "
                "seasons since NIL rules took effect. No rating in this study uses these games.")
    ax = fig.add_axes([0.16, 0.25, 0.78, 0.44])
    y = list(range(len(groups)))[::-1]
    h = 0.34
    for yy, g in zip(y, groups):
        a, b = ps["2014-2019"][g]["all_postseason"], ps["2021-2025"][g]["all_postseason"]
        ax.barh(yy + h / 2 + 0.02, a["win_share"] * 100, height=h, color=OTHER)
        ax.barh(yy - h / 2 - 0.02, b["win_share"] * 100, height=h, color=HIGHLIGHT if g == "SEC" else SECOND if g == "Big Ten" else "#8fb6e6")
        ax.text(a["win_share"] * 100 + 1, yy + h / 2 + 0.02, f"{a['win_share']:.0%}  ({a['wins']}–{a['losses']})",
                va="center", fontsize=9, color=INK2)
        ax.text(b["win_share"] * 100 + 1, yy - h / 2 - 0.02, f"{b['win_share']:.0%}  ({b['wins']}–{b['losses']})",
                va="center", fontsize=9, color=INK)
    ax.axvline(50, color=INK2, lw=1, ls=(0, (3, 3)), zorder=0)
    ax.set_yticks(y)
    ax.set_yticklabels(groups, fontsize=11)
    ax.set_xlim(0, 88)
    ax.set_xticks([0, 25, 50, 75])
    ax.set_xticklabels(["0%", "25%", "50%", "75%"], fontsize=9)
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    fig.text(0.16, 0.705, "Top bar: 2014–2019   Bottom bar: 2021–2025", fontsize=8.5, color=INK2)
    t8 = era["polls_T8_same_record_premium_SEC"]
    ch = ps["national_champions"]
    big10 = [s for s, c in ch.items() if c["group"] == "Big Ten" and int(s) >= 2021]
    note(fig, f"Meanwhile the AP's same-record premium for SEC teams went from +{t8['early_2014_2019']:.1f} to "
         f"+{t8['recent_2021_2025']:.1f} places (not statistically clear over so few seasons). Last three champions: "
         f"Big Ten ({', '.join(big10)}). Bowls carry opt-outs; read as one more signal, not a clean test.")
    save(fig, "09_postseason.png")


def main():
    n = json.loads((RES / "post_numbers.json").read_text())
    miami(n)
    levels(n)
    stages(n)
    schedules(n)
    same_resume(n)
    head_start(n)
    robustness(n)
    external(n)
    postseason(n)


if __name__ == "__main__":
    main()
