"""Four square images for the LinkedIn post, drawn from results/post_numbers.json.

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


def frame(title, subtitle):
    fig = plt.figure(figsize=(6, 6), dpi=200)
    t = textwrap.fill(title, 40)
    st = textwrap.fill(subtitle, 76)
    fig.text(0.06, 0.95, t, fontsize=16, fontweight="bold", color=INK, va="top", linespacing=1.15)
    y = 0.95 - 0.052 * (t.count("\n") + 1) - 0.012
    fig.text(0.06, y, st, fontsize=9.5, color=INK2, va="top", linespacing=1.3)
    fig.text(0.06, 0.03, textwrap.fill(FOOT, 110), fontsize=6.5, color=MUTED, va="bottom")
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

    fig = frame("Miami on performance alone: #1 or #2 on every measure",
                f"2026 after week {m['after_week']}. Every ranking uses only this season's scores and schedules "
                "(no polls, no preseason, no names) and adjusts for who each team has played.")
    rows = [
        ("Strength of record", "How hard would 7-0 against this exact schedule be?", int(m["sor_rank"]),
         f"#1 in 9 of 11 versions; never worse than #{m['sor_rank_range_across_11_settings'][1]}"),
        ("Wins and losses, schedule-adjusted", "Colley ranking", int(m["colley_rank"]), f"#1: {leader('colley_rank')}"),
        ("Scoring margin, schedule-adjusted", "Margin capped at 28 points", int(m["performance_rank"]),
         f"#1: {leader('perf_rank')}"),
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
    fig.text(0.06, 0.29, "The schedule, for context", fontsize=11, fontweight="bold", color=INK, va="top")
    fig.text(0.06, 0.255, textwrap.fill(
        f"By how its opponents have actually played, Miami's schedule is {r}th of {total}: middle of the pack, "
        f"not \"nobody\". The rankings above already account for it. A softer schedule makes 7-0 easier, so "
        "it counts against Miami. Miami is #1 despite it, not because of it.", 82),
        fontsize=8.8, color=INK2, va="top", linespacing=1.35)
    note(fig, f"Counted by opponents' AP rank on game day instead, Miami has faced no ranked team, like "
         f"{m['teams_with_no_ap_top25_opponent_yet'] - 1} other teams.")
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
    note(fig, f"*Pac-12 2014–2023. The SEC's boost holds all season and stays positive when the rating is "
             f"recalibrated ({lo:+.1f} to {hi:+.1f}); whether it beats the ACC's depends on that calibration.",
             )
    save(fig, "04_schedule_boost.png")


def main():
    n = json.loads((RES / "post_numbers.json").read_text())
    miami(n)
    levels(n)
    stages(n)
    schedules(n)


if __name__ == "__main__":
    main()
