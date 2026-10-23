"""Draw every figure in REPORT.md from the committed result files. Offline only.

Writes PNGs to results/figures/. Colors follow the entity across all figures:
SEC blue, ACC orange, other conferences gray; the final (rated) model aqua,
earlier models and baselines in grays. Values behind every figure are in the
results/*.json files and the tables in REPORT.md.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
FIG = RES / "figures"
PROC = ROOT / "data" / "processed"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SEC = "#2a78d6"
ACC = "#eb6834"
FINAL = "#1baf7a"
GRAY_LIGHT = "#c3c2b7"
GRAY_MID = "#898781"
GRAY_DARK = "#52514e"
CONF_COLOR = {"SEC": SEC, "ACC": ACC, "Big Ten": GRAY_MID, "Big 12": GRAY_MID, "Other": GRAY_LIGHT}
CONFS = ["SEC", "ACC", "Big Ten", "Big 12", "Other"]
CONF_LABEL = {"Other": "Other (Pac-12, G5, ind.)"}
SPEC_COLOR = {"registered": GRAY_LIGHT, "revised": GRAY_DARK, "rated": FINAL}
SPEC_LABEL = {"registered": "Registered model", "revised": "Revised model", "rated": "Rated model (final)"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.labelcolor": INK2, "axes.edgecolor": AXIS,
    "axes.linewidth": 1, "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelcolor": INK2, "ytick.labelcolor": INK2, "text.color": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False, "legend.fontsize": 9, "lines.linewidth": 2,
    "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
})


def load(name):
    return json.loads((RES / name).read_text())


def save(fig, name, note=None):
    if note:
        fig.canvas.draw()
        bottom = fig.get_tightbbox(fig.canvas.get_renderer()).y0
        fig.text(0.01, (bottom - 0.06) / fig.get_figheight(), note, fontsize=8, color=MUTED,
                 ha="left", va="top")
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=200, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)


def dot(ax, x, y, color, size=8, **kw):
    ax.plot(x, y, "o", ms=size, color=color, mec=SURFACE, mew=1.5, **kw)


def forest(ax, rows, title, xlabel, zero=0.0):
    """rows: list of (label, mean, lo, hi, color); top to bottom."""
    for i, (label, m, lo, hi, color) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.plot([lo, hi], [y, y], color=color, lw=2)
        dot(ax, m, y, color, size=9, zorder=3)
        ax.annotate(f"{m:+.2f}", (hi, y), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK2)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows][::-1])
    ax.axvline(zero, color=AXIS, lw=1, zorder=1)
    ax.grid(axis="y", visible=False)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    lo_all = min(r[2] for r in rows)
    hi_all = max(r[3] for r in rows)
    pad = 0.25 * (hi_all - lo_all)
    ax.set_xlim(min(lo_all, zero) - pad * 0.3, max(hi_all, zero) + pad)


def conf_rows(block, key_mean="mean", key_ci="ci"):
    return [(CONF_LABEL.get(c, c), block[c][key_mean], block[c][key_ci][0], block[c][key_ci][1],
             CONF_COLOR[c]) for c in CONFS]


# ---------------------------------------------------------------- process & data

def fig_timeline():
    events = [
        ("17:15", "Methodology committed (before any data)"),
        ("17:18", "Raw data frozen with checksums"),
        ("17:21", "Data verified; poll depth deviation logged"),
        ("17:36", "Models trained on 2014-2023; selection rule frozen"),
        ("18:12", "Model revisions logged (before holdout)"),
        ("18:38", "2024-2025 holdout scored once"),
        ("18:42", "2026 counterfactual run as logged"),
        ("18:48", "Hypothesis tests run (Elo yardstick)"),
        ("18:56", "Season-only rating logged to replace Elo"),
        ("19:06", "Rated model and bias tests logged"),
        ("19:18", "First full set of results committed"),
        ("20:27", "Outside review: H5 sensitivity logged"),
        ("20:30", "Raw-data removal logged (CFBD terms)"),
        ("20:34", "Findings rewritten after review"),
        ("20:37", "Single-threaded training logged"),
    ]
    t = [int(h) * 60 + int(m) for h, m in (e[0].split(":") for e in events)]
    fig, ax = plt.subplots(figsize=(9, 5.8))
    ax.plot(t, range(len(t))[::-1], color=GRID, lw=2, zorder=1)
    for i, (ti, (clock, label)) in enumerate(zip(t, events)):
        y = len(t) - 1 - i
        color = (FINAL if "holdout" in label else SEC if "Methodology" in label
                 else ACC if t[i] >= 20 * 60 + 27 else GRAY_DARK)
        dot(ax, ti, y, color, size=9, zorder=3)
        ax.annotate(f"{clock}  {label}", (ti, y), xytext=(10, 0), textcoords="offset points",
                    va="center", fontsize=9, color=INK)
    ax.set_yticks([])
    ax.grid(axis="y", visible=False)
    ax.set_xlim(t[0] - 10, t[-1] + 150)
    ticks = list(range(17 * 60, 21 * 60 + 1, 30))
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{x // 60}:{x % 60:02d}" for x in ticks])
    ax.set_xlabel("Commit time, 2026-10-23 (UTC)")
    ax.set_title("Audit trail: the plan was committed before any data or result")
    ax.spines["left"].set_visible(False)
    save(fig, "fig01_timeline.png", "Every change to the plan is dated in DEVIATIONS.md and was committed before use. "
         "Orange: fixes after an outside review.")


def fig_data_overview():
    tw = pd.read_csv(PROC / "team_weeks.csv", usecols=["season", "voters_prior", "week"])
    counts = tw.groupby("season").size()
    voters = tw.groupby("season").voters_prior.agg(["min", "max", "mean"])
    seasons = [s for s in range(2014, 2027)]
    x = np.arange(len(seasons))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.8))
    split = {s: ("Training" if s <= 2023 else "Holdout" if s <= 2025 else "2026 (to date)") for s in seasons}
    colors = {"Training": GRAY_DARK, "Holdout": FINAL, "2026 (to date)": SEC}
    for i, s in enumerate(seasons):
        if s in counts.index:
            a1.bar(i, counts[s], width=0.6, color=colors[split[s]])
        else:
            a1.annotate("2020\nexcluded", (i, 80), ha="center", fontsize=8, color=MUTED)
    a1.legend(handles=[Patch(color=c, label=lab) for lab, c in colors.items()],
              loc="upper left", ncol=3)
    a1.set_xticks(x)
    a1.set_xticklabels([str(s)[2:] for s in seasons])
    a1.set_ylim(0, counts.max() * 1.18)
    a1.set_ylabel("Team-weeks (FBS team x poll transition)")
    a1.set_xlabel("Season (20xx)")
    a1.set_title("21,626 team-weeks across 12 seasons")
    a1.grid(axis="x", visible=False)
    vs = [s for s in seasons if s in voters.index]
    xv = [seasons.index(s) for s in vs]
    a2.fill_between(xv, voters.loc[vs, "min"], voters.loc[vs, "max"], color=SEC, alpha=0.12, lw=0)
    a2.plot(xv, voters.loc[vs, "mean"], color=SEC, marker="o", ms=6, mec=SURFACE, mew=1.5)
    a2.set_xticks(x)
    a2.set_xticklabels([str(s)[2:] for s in seasons])
    a2.set_ylabel("AP voters per poll")
    a2.set_xlabel("Season (20xx)")
    a2.set_title("The AP panel grew, so points are scaled per voter")
    a2.annotate(f"{voters.loc[2026, 'mean']:.0f}", (xv[-1], voters.loc[2026, "mean"]),
                xytext=(6, 0), textcoords="offset points", va="center", fontsize=9, color=INK2)
    a2.annotate(f"{voters.loc[2014, 'mean']:.0f}", (xv[0], voters.loc[2014, "mean"]),
                xytext=(-6, 8), textcoords="offset points", ha="right", fontsize=9, color=INK2)
    save(fig, "fig02_data_overview.png", "Band: lowest to highest voter count in a season; line: season mean.")


# ---------------------------------------------------------------- training

def fig_training_mae():
    m = load("train_metrics.json")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 3.9), gridspec_kw={"width_ratios": [1.4, 1]})
    fig.subplots_adjust(wspace=0.45)
    by = m["rated"]["zero"]["by_season"]
    seasons = sorted(by, key=int)
    x = np.arange(len(seasons))
    for name, color, lab in (("baseline", GRAY_LIGHT, "Predict no change"),
                             ("linear", GRAY_DARK, "Linear"),
                             ("gbt", FINAL, "Boosted trees")):
        a1.plot(x, [by[s][name] for s in seasons], color=color, marker="o", ms=7,
                mec=SURFACE, mew=1.5, label=lab)
    a1.set_xticks(x)
    a1.set_xticklabels(seasons)
    a1.set_ylim(0, 1.35)
    a1.set_ylabel("Mean absolute error (AP points per voter)")
    a1.set_title("Each training season, predicted by a model that never saw it")
    a1.legend(loc="upper left", ncol=3)
    specs = ["registered", "revised", "rated"]
    ratio = {s: {k: m[s]["zero"]["ranked_teams_only"][k] / m[s]["zero"]["ranked_teams_only"]["baseline"]
                 for k in ("linear", "gbt")} for s in specs}
    y = np.arange(len(specs))
    a2.barh(y + 0.18, [ratio[s]["linear"] for s in specs], height=0.32, color=GRAY_DARK, label="Linear")
    a2.barh(y - 0.18, [ratio[s]["gbt"] for s in specs], height=0.32, color=FINAL, label="Boosted trees")
    for i, s in enumerate(specs):
        for off, k in ((0.18, "linear"), (-0.18, "gbt")):
            a2.annotate(f"{ratio[s][k]:.2f}", (ratio[s][k], i + off), xytext=(4, 0),
                        textcoords="offset points", va="center", fontsize=8, color=INK2)
    a2.axvline(1, color=AXIS, lw=1)
    a2.annotate("= no change", (1, -0.45), xytext=(4, 0), textcoords="offset points",
                fontsize=8, color=MUTED, va="center")
    a2.set_yticks(y)
    a2.set_yticklabels([SPEC_LABEL[s].replace(" (final)", "") for s in specs])
    a2.invert_yaxis()
    a2.set_xlim(0, 1.25)
    a2.grid(axis="y", visible=False)
    a2.set_xlabel("Error relative to predicting no change (ranked teams)")
    a2.set_title("Trees cut error by about 70%")
    a2.legend(loc="upper right")
    save(fig, "fig03_training_error.png", "Rated specification, unranked = 0. Linear is worse than no change on all teams.")


def fig_replay_training():
    rt = load("replay_training.json")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.9))
    for spec in ("registered", "revised", "rated"):
        c = pd.read_csv(RES / f"replay_training_curve_{spec}_gbt_zero.csv")
        g = c.groupby("poll_week").spearman.mean()
        a1.plot(g.index, g.values, color=SPEC_COLOR[spec], label=SPEC_LABEL[spec])
    a1.axhline(0.7, color=AXIS, lw=1)
    a1.annotate("pass bar 0.70", (16, 0.7), xytext=(0, -12), textcoords="offset points",
                ha="right", fontsize=8, color=MUTED)
    a1.set_ylim(0.5, 1.0)
    a1.set_xlabel("Poll week (replay starts from the preseason poll)")
    a1.set_ylabel("Rank correlation with real poll")
    a1.set_title("Replay accuracy fades as errors compound")
    a1.legend(loc="lower left")
    seasons = [s for s in range(2014, 2024) if s != 2020]
    x = np.arange(len(seasons))
    offs = {"registered": -0.2, "revised": 0, "rated": 0.2}
    for spec in ("registered", "revised", "rated"):
        v = [rt[f"{spec}_gbt_zero"]["by_season"][str(s)]["final_regular"]["spearman"] for s in seasons]
        for xi, vi in zip(x + offs[spec], v):
            dot(a2, xi, vi, SPEC_COLOR[spec], size=8)
    base = [rt["rated_gbt_zero"]["by_season"][str(s)]["preseason_unchanged_vs_final_regular"]["spearman"]
            for s in seasons]
    a2.plot(x, base, ls="none", marker="_", ms=14, mew=2, color=ACC, label="Preseason poll held fixed")
    for spec in ("registered", "revised", "rated"):
        a2.plot([], [], "o", color=SPEC_COLOR[spec], label=SPEC_LABEL[spec])
    a2.axhline(0.7, color=AXIS, lw=1)
    a2.set_xticks(x)
    a2.set_xticklabels(seasons)
    a2.set_ylim(0.2, 1.0)
    a2.set_ylabel("Rank correlation, final regular-season poll")
    a2.set_title("Final poll, every training season")
    a2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), fontsize=8, ncol=2)
    save(fig, "fig04_replay_training.png", "Each season replayed by a model fit without it. Unranked = 0.")


def fig_climbers():
    rt = load("replay_training.json")
    specs = ["registered", "revised", "rated"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.4))
    y = np.arange(len(specs))
    caught = [rt[f"{s}_gbt_zero"]["summary"]["climbers_caught"] for s in specs]
    real = rt["rated_gbt_zero"]["summary"]["climbers_real"]
    a1.barh(y, caught, height=0.5, color=[SPEC_COLOR[s] for s in specs])
    a1.axvline(real, color=AXIS, lw=1)
    a1.annotate(f"{real} real climbers", (real, -0.45), xytext=(-4, 0), textcoords="offset points",
                ha="right", fontsize=8, color=MUTED, va="center")
    for i, v in enumerate(caught):
        a1.annotate(str(v), (v, i), xytext=(4, 0), textcoords="offset points", va="center", fontsize=9)
    a1.set_yticks(y)
    a1.set_yticklabels([SPEC_LABEL[s] for s in specs])
    a1.invert_yaxis()
    a1.set_xlim(0, 100)
    a1.grid(axis="y", visible=False)
    a1.set_xlabel("Teams correctly promoted from unranked into the final top 25")
    a1.set_title("Catching teams that climb in")
    st = [rt[f"{s}_gbt_zero"]["summary"]["stickiness_spots_mean"] for s in specs]
    a2.barh(y, st, height=0.5, color=[SPEC_COLOR[s] for s in specs])
    for i, v in enumerate(st):
        a2.annotate(f"+{v:.2f}", (v, i), xytext=(4, 0), textcoords="offset points", va="center", fontsize=9)
    a2.set_yticks(y)
    a2.set_yticklabels([])
    a2.invert_yaxis()
    a2.set_xlim(0, 1.6)
    a2.grid(axis="y", visible=False)
    a2.set_xlabel("Rank places preseason-ranked teams are kept too high")
    a2.set_title("Stickiness to the preseason poll")
    save(fig, "fig05_climbers_stickiness.png", "Training seasons 2014-2023 (no 2020), nine seasons pooled. Unranked = 0.")


# ---------------------------------------------------------------- holdout

def fig_holdout():
    h = load("holdout.json")
    r = load("holdout_reuse_rated.json")
    rows = [("Registered, 0 rule", h["registered_zero"], GRAY_LIGHT),
            ("Registered, floor rule", h["registered_floor"], GRAY_LIGHT),
            ("Revised, 0 rule (primary)", h["revised_zero"], GRAY_DARK),
            ("Revised, floor rule", h["revised_floor"], GRAY_DARK),
            ("Rated, 0 rule (holdout re-used)", r["rated_zero"], FINAL)]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    for i, (lab, d, color) in enumerate(rows):
        y = len(rows) - 1 - i
        v = [d["replay"][s]["final_regular"]["spearman"] for s in ("2024", "2025")]
        ax.plot(v, [y, y], color=GRID, lw=2, zorder=1)
        ax.plot(v[0], y, "s", ms=8, color=color, mec=SURFACE, mew=1.5, zorder=3)
        ax.plot(v[1], y, "o", ms=9, color=color, mec=SURFACE, mew=1.5, zorder=3)
        ax.annotate(f"{v[0]:.2f} / {v[1]:.2f}", (max(v), y), xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK2)
    pre = [h["revised_zero"]["replay"][s]["preseason_unchanged_vs_final_regular"]["spearman"]
           for s in ("2024", "2025")]
    ax.axvspan(0.4, 0.7, color="#f0efec", zorder=0, lw=0)
    ax.axvline(0.7, color=AXIS, lw=1)
    ax.annotate("fails below 0.70", (0.69, len(rows) - 0.2), ha="right", fontsize=8, color=MUTED)
    ax.annotate(f"preseason poll held fixed: {pre[0]:.2f} (2024), {pre[1]:.2f} (2025)",
                (0.41, -0.75), fontsize=8, color=MUTED)
    ax.plot([], [], "s", color=GRAY_DARK, label="2024")
    ax.plot([], [], "o", color=GRAY_DARK, label="2025")
    ax.legend(loc="center left")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows][::-1])
    ax.set_ylim(-1.1, len(rows) + 0.1)
    ax.set_xlim(0.4, 1.05)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Rank correlation of replayed vs real final regular-season poll")
    ax.set_title("Holdout 2024-2025, scored once: the primary model passes")
    save(fig, "fig06_holdout.png", "Rated model defined after the holdout was used; shown for reference, not a clean test.")


def fig_holdout_scatter():
    h = load("holdout.json")["revised_zero"]["replay"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=True)
    for ax, s in zip(axes, ("2024", "2025")):
        real = h[s]["real_top25"]
        sim = {t: i + 1 for i, t in enumerate(h[s]["sim_top25"])}
        x = np.arange(1, len(real) + 1)
        y = [sim.get(t, 27) for t in real]
        ax.plot([1, 25], [1, 25], color=AXIS, lw=1, zorder=1)
        ax.axhspan(25.5, 28, color="#f0efec", lw=0, zorder=0)
        for xi, yi, t in zip(x, y, real):
            color = FINAL if yi <= 25 else ACC
            dot(ax, xi, yi, color, size=8, zorder=3)
            if yi <= 25 and (abs(yi - xi) >= 6 or xi == 1):
                ax.annotate(t, (xi, yi), xytext=(6, 2), textcoords="offset points", fontsize=7, color=INK2)
        missed = [t for t, yi in zip(real, y) if yi > 25]
        lines, cur = [], ""
        for t in missed:
            cur = f"{cur}, {t}" if cur else t
            if len(cur) > 34:
                lines.append(cur)
                cur = ""
        if cur:
            lines.append(cur)
        ax.annotate("Left out by the replay:\n" + ",\n".join(lines), (0.03, 0.2), xycoords="axes fraction",
                    fontsize=7, color=INK2, va="bottom")
        ax.set_xlim(0, 26.5)
        ax.set_ylim(28, 0)
        ax.set_xticks([1, 5, 10, 15, 20, 25])
        ax.set_yticks([1, 5, 10, 15, 20, 25, 27])
        ax.set_yticklabels(["1", "5", "10", "15", "20", "25", "not in\ntop 25"])
        ax.set_xlabel(f"Real final regular-season rank, {s}")
        rho = h[s]["final_regular"]["spearman"]
        ax.set_title(f"{s}: replay from preseason, rho = {rho:.2f}")
    axes[0].set_ylabel("Replayed rank (primary model)")
    save(fig, "fig07_holdout_placement.png",
         "Diagonal = perfect placement. Orange: real top-25 teams the replay left out (mostly risers from outside the preseason poll).")


# ---------------------------------------------------------------- strength rating & Elo

def fig_rating_validation():
    v = load("season_rating_validation.json")["accuracy_games_with_a_ranked_team"]
    rows = [("Season-only rating (combined)", v["combined"], FINAL),
            ("  results part (Colley)", v["results"], GRAY_MID),
            ("  performance part (margins)", v["performance"], GRAY_MID),
            ("Elo (uses last season)", v["elo"], GRAY_DARK),
            ("AP poll (better-ranked team)", v["ap"], SEC)]
    fig, ax = plt.subplots(figsize=(8.5, 3.2))
    y = np.arange(len(rows))
    ax.barh(y, [r[1] * 100 for r in rows], height=0.5, color=[r[2] for r in rows])
    for i, r in enumerate(rows):
        ax.annotate(f"{r[1]:.1%}", (r[1] * 100, i), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(50, 80)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Next-week winners picked correctly (%)")
    ax.set_title("Our season-only rating predicts as well as Elo and the AP poll")
    save(fig, "fig08_rating_validation.png",
         "1,769 FBS games in week 6+ of 2014-2025 involving a ranked team. Axis starts at 50% (a coin flip).")


def fig_elo_carryover():
    rows = []
    for y in [s for s in range(2014, 2027) if s != 2020]:
        s = pd.read_parquet(ROOT / "data" / "raw" / "schedules" / f"cfb_schedules_{y}.parquet")
        s = s[(s.home_division == "fbs") & (s.away_division == "fbs") & s.completed]
        for side in ("home", "away"):
            rows.append(pd.DataFrame({"season": y, "d": s.start_date, "team": s[f"{side}_team"],
                                      "pre": s[f"{side}_pregame_elo"], "post": s[f"{side}_postgame_elo"]}))
    long = pd.concat(rows).dropna().sort_values("d")
    end = long.groupby(["season", "team"]).post.last()
    start = long.groupby(["season", "team"]).pre.first()
    pairs = [(end[(s, t)], start[(s + 1, t)]) for (s, t) in end.index if (s + 1, t) in start.index]
    e, st = np.array(pairs).T
    b = np.polyfit(e - 1500, st - 1500, 1)
    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.plot(e, st, "o", ms=3, color=GRAY_MID, alpha=0.35, mew=0)
    xs = np.array([e.min(), e.max()])
    ax.plot(xs, 1500 + b[0] * (xs - 1500) + b[1], color=SEC)
    ax.plot(xs, xs, color=AXIS, lw=1)
    ax.annotate(f"next preseason Elo = 1500 + {b[0]:.2f} x (last final - 1500)\n"
                f"correlation {np.corrcoef(e, st)[0, 1]:.2f}, {len(e):,} team-seasons",
                (0.03, 0.97), xycoords="axes fraction", va="top", fontsize=9, color=INK)
    ax.annotate("y = x (no pull toward average)", (1050, 1050), xytext=(6, -4), textcoords="offset points",
                fontsize=8, color=MUTED, va="top")
    ax.set_xlabel("Elo at the end of a season")
    ax.set_ylabel("Elo at the start of the next season")
    ax.set_title("Elo carries two-thirds of last season forward")
    save(fig, "fig09_elo_carryover.png", "Why Elo cannot detect a preseason head start: it carries one too.")


# ---------------------------------------------------------------- hypothesis tests

def fig_poll_vs_strength():
    h = load("hypothesis.json")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
    forest(a1, conf_rows(h["poll_vs_elo"], "mean_gap"), "Against Elo (carries last season)",
           "Poll rank above strength rank (places)")
    forest(a2, conf_rows(h["season_rating"]["poll_vs_rating"], "mean_gap"),
           "Against this season's results only", "Poll rank above strength rank (places)")
    save(fig, "fig10_poll_vs_strength.png",
         "Dot: mean; line: 95% interval (team-season bootstrap). Positive = the poll ranks teams above their strength. 2014-2025.")


def fig_poll_vs_strength_counts():
    pv = load("hypothesis.json")["season_rating"]["poll_vs_rating"]
    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    y = np.arange(len(CONFS))
    over = [pv[c]["ap_ranked_outside_elo_top25"] for c in CONFS]
    under = [pv[c]["elo_top25_ap_unranked"] for c in CONFS]
    ax.barh(y, over, height=0.5, color=[CONF_COLOR[c] for c in CONFS])
    ax.barh(y, [-u for u in under], height=0.5, color=[CONF_COLOR[c] for c in CONFS], alpha=0.45)
    for i in range(len(CONFS)):
        ax.annotate(str(over[i]), (over[i], i), xytext=(4, 0), textcoords="offset points", va="center", fontsize=9)
        ax.annotate(str(under[i]), (-under[i], i), xytext=(-4, 0), textcoords="offset points",
                    va="center", ha="right", fontsize=9)
    ax.axvline(0, color=AXIS, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels([CONF_LABEL.get(c, c) for c in CONFS])
    ax.invert_yaxis()
    lim = max(max(over), max(under)) * 1.25
    ax.set_xlim(-lim, lim)
    ax.set_xticks(ax.get_xticks())
    ax.set_xticklabels([str(abs(int(t))) for t in ax.get_xticks()])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Team-weeks, polls 6+, 2014-2025")
    ax.annotate("left: in our top 25, AP left them out", (0.01, 1.02), xycoords="axes fraction",
                fontsize=8, color=MUTED)
    ax.annotate("right: AP-ranked, outside our top 25", (0.99, 1.02), xycoords="axes fraction",
                fontsize=8, color=MUTED, ha="right")
    ax.set_title("Who the poll ranks that results don't support", pad=18)
    save(fig, "fig11_snubs_and_gifts.png")


def fig_carryover():
    h = load("hypothesis.json")
    rows = []
    for lab, block, color in (("Controlling Elo", h["zero"]["preseason_carryover"], GRAY_DARK),
                              ("Controlling season-only rating",
                               h["season_rating"]["preseason_carryover"]["zero"], FINAL)):
        rows.append((lab, block["preseason_coef"], *block["preseason_coef_ci"], color))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 2.8))
    forest(a1, rows, "About half of preseason standing persists", "Carry-over coefficient")
    a1.set_xlim(0, 0.75)
    a1.set_ylim(-0.6, 1.6)
    rows2 = []
    for lab, block, color in (("Controlling Elo", h["zero"]["preseason_carryover"], GRAY_DARK),
                              ("Controlling season-only rating",
                               h["season_rating"]["preseason_carryover"]["zero"], FINAL)):
        rows2.append((lab, block["sec_minus_acc"], *block["sec_minus_acc_ci"], color))
    forest(a2, rows2, "...and no more for the SEC than the ACC", "Extra carry-over, SEC minus ACC")
    a2.set_yticklabels([])
    a2.set_ylim(-0.6, 1.6)
    save(fig, "fig12_preseason_carryover.png",
         "Points per voter later in the season per point per voter in the preseason poll, at equal record, margin, strength and week.")


def fig_conference_effect():
    h = load("hypothesis.json")["zero"]["conference_effect"]["revised"]
    rows = [(c, h["coef"][c], h["coef"][c], h["coef"][c], CONF_COLOR[c]) for c in ["SEC", "ACC", "Big Ten", "Big 12"]]
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    forest(ax, rows, "H1: extra points for the same result (linear model)",
           "Coefficient vs Other conferences (points per voter per week)")
    ax.annotate(f"SEC minus ACC: {h['sec_minus_acc']:+.2f} (95% CI {h['sec_minus_acc_ci'][0]:+.2f} to "
                f"{h['sec_minus_acc_ci'][1]:+.2f})", (0.0, -0.42), xycoords="axes fraction",
                fontsize=9, color=INK2)
    save(fig, "fig13_conference_effect.png",
         "Caution: the linear model fits worse than predicting no change; Fig. 14 uses the far better model.")


def fig_rewards():
    b = load("bias_tests.json")["rewards_and_punishments"]["zero"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
    forest(a1, conf_rows(b["ranked_after_win"]), "After a win: rewarded more than results explain?",
           "Residual, points per voter (+ = rose more)")
    forest(a2, conf_rows(b["ranked_after_loss"]), "After a loss: punished less than results explain?",
           "Residual, points per voter (+ = fell less)")
    save(fig, "fig14_rewards_punishments.png",
         "Name-blind rated model, each 2014-2025 season predicted out of sample. Ranked teams. One rank place is about 0.8.")


def fig_schedule_inflation():
    b = load("bias_tests.json")["schedule_inflation_2014_2025"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.2), gridspec_kw={"width_ratios": [1.2, 1]})
    fig.subplots_adjust(wspace=0.55)
    for i, c in enumerate(CONFS):
        p, r = b[c]["mean_poll_sos_rank"], b[c]["mean_rating_sos_rank"]
        a1.plot([p, r], [i, i], color=GRID, lw=3, zorder=1)
        a1.plot(p, i, "o", ms=10, color=CONF_COLOR[c], mec=SURFACE, mew=1.5, zorder=3)
        a1.plot(r, i, "o", ms=10, mfc=SURFACE, mec=CONF_COLOR[c], mew=2, zorder=3)
        a1.annotate(f"{p:.0f}", (p, i), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8, color=INK2)
        a1.annotate(f"{r:.0f}", (r, i), xytext=(0, -15), textcoords="offset points", ha="center", fontsize=8, color=INK2)
    a1.plot([], [], "o", color=GRAY_DARK, label="ranked by opponents' poll standing")
    a1.plot([], [], "o", mfc=SURFACE, mec=GRAY_DARK, mew=2, label="ranked by opponents' actual results")
    a1.legend(loc="upper left", fontsize=8)
    a1.set_yticks(range(len(CONFS)))
    a1.set_yticklabels([CONF_LABEL.get(c, c) for c in CONFS])
    a1.set_ylim(len(CONFS) - 0.4, -1.3)
    a1.set_xlim(0, 100)
    a1.invert_xaxis()
    a1.grid(axis="y", visible=False)
    a1.set_xlabel("Average schedule-strength rank among FBS teams (1 = toughest)")
    a1.set_title("H5 as originally computed")
    rows = conf_rows(b) + [("SEC minus ACC", b["sec_minus_acc"], *b["sec_minus_acc_ci"], INK)]
    forest(a2, rows, "Inflation, with 95% interval", "Rating rank minus poll rank (places)")
    save(fig, "fig15_schedule_inflation.png",
         "As originally computed. The ACC figure is mostly a measurement artifact: see the shape-matched check (Fig. 21).\n"
         "2014-2025 team-seasons. Positive inflation = schedule looks tougher by poll than by results. "
         "Other is sensitive to ties (+1.3 with average ranks).")


def fig_head_start():
    b = load("bias_tests.json")["head_start_elo_vs_season_rating"]
    rows = conf_rows(b) + [("SEC minus ACC", b["sec_minus_acc"], *b["sec_minus_acc_ci"], INK)]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    forest(ax, rows, "Elo's carried-over head start, relative to this season's results",
           "Places Elo ranks teams above the season-only rating")
    save(fig, "fig16_elo_head_start.png", "Polls 6+, 2014-2025. Positive = Elo rates the team above its current-season results.")


def fig_base_rates():
    b = load("base_rates_poll8.json")
    order = ["P4, started unranked, 6-1 or better", "P4, started ranked, 6-1 or better",
             "P4, started unranked, 5-1 or better", "P4, started ranked, 5-1 or better",
             "Started top 12, 3+ losses", "Started 13-25, 3+ losses", "Started unranked, 3+ losses"]
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    y = np.arange(len(order))
    vals = [b[k]["ranked_in_poll_8"] * 100 for k in order]
    colors = [SEC if "started ranked" in k.lower() or "top 12" in k or "13-25" in k else GRAY_MID for k in order]
    ax.barh(y, vals, height=0.5, color=colors)
    for i, k in enumerate(order):
        ax.annotate(f"{vals[i]:.0f}%  (n={b[k]['team_seasons']})", (vals[i], i), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=9)
    ax.legend(handles=[Patch(color=SEC, label="started ranked"),
                       Patch(color=GRAY_MID, label="started unranked")], loc="lower right")
    ax.set_yticks(y)
    ax.set_yticklabels([k.replace("P4, ", "Power-4, ") for k in order])
    ax.invert_yaxis()
    ax.set_xlim(0, 125)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Ranked in poll 8 (%)")
    ax.set_title("What real voters do after seven weeks: record mostly wins out")
    save(fig, "fig17_base_rates.png", "Real AP polls 2014-2025 (no 2020); no model involved.")


# ---------------------------------------------------------------- counterfactual

def fig_counterfactual_slots():
    c = load("counterfactual_2026_rated.json")["zero"]
    last = max(c["sanity"], key=int)
    runs = [("Real AP poll", c["conference_slots"]["real"][last]),
            ("Model, no swap", c["conference_slots"]["no_swap"][last]),
            ("3 pairs swapped", c["swap3"]["conference_slots"][last]),
            ("9 slots swapped", c["swap9"]["conference_slots"][last])]
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    x = np.arange(len(runs))
    w = 0.32
    for off, conf, color in ((-w / 2 - 0.02, "SEC", SEC), (w / 2 + 0.02, "ACC", ACC)):
        vals = [r[1][conf] for r in runs]
        ax.bar(x + off, vals, width=w, color=color, label=conf)
        for xi, v in zip(x + off, vals):
            ax.annotate(str(v), (xi, v), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([r[0] for r in runs])
    ax.set_ylim(0, 12)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel(f"Top-25 slots at poll {last}")
    ax.legend(loc="upper right")
    ax.set_title("2026 swap (rated model): every model run fails the reality check")
    save(fig, "fig18_counterfactual_slots.png",
         "Not evidence: every run, including the no-swap run, fails the plausibility check.\n"
         "Model runs leave 6-1 Wake Forest unranked and keep 3-3 Oklahoma ranked; the real poll does neither.")


def fig_counterfactual_teams():
    c = load("counterfactual_2026_rated.json")["zero"]["swap9"]["teams"]
    t = sorted(c, key=lambda d: d["final_gain"])
    fig, ax = plt.subplots(figsize=(8.5, 6))
    for i, d in enumerate(t):
        f = d["weekly"][-1]
        color = SEC if d["conference"] == "SEC" else ACC
        ax.plot([f["no_swap"], f["swap"]], [i, i], color=GRID, lw=3, zorder=1)
        ax.plot(f["no_swap"], i, "o", ms=8, mfc=SURFACE, mec=color, mew=2, zorder=3)
        ax.plot(f["swap"], i, "o", ms=9, color=color, mec=SURFACE, mew=1.5, zorder=3)
    ax.plot([], [], "o", mfc=SURFACE, mec=GRAY_DARK, mew=2, label="simulated, no swap")
    ax.plot([], [], "o", color=GRAY_DARK, label="simulated, with swap")
    ax.plot([], [], "s", color=SEC, label="SEC team")
    ax.plot([], [], "s", color=ACC, label="ACC team")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), fontsize=8, ncol=4)
    ax.set_yticks(range(len(t)))
    ax.set_yticklabels([f"{d['team']} (with {d['partner']}'s slot)" for d in t], fontsize=8)
    ax.set_xlim(27, 0)
    ax.set_xticks([1, 5, 10, 15, 20, 25, 26])
    ax.set_xticklabels(["1", "5", "10", "15", "20", "25", "out"])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Rank at poll 8 (right = better)")
    ax.set_title("Nine-slot swap: who moves (model output, failed plausibility)")
    save(fig, "fig19_counterfactual_teams.png",
         "Not evidence: every run, including the no-swap run, fails the plausibility check.\n"
         "Rated model, unranked = 0. Shown for transparency; see REPORT.md 5.6.")


def fig_2026_now():
    tw = pd.read_csv(PROC / "team_weeks.csv")
    r = pd.read_csv(PROC / "season_ratings.csv")
    last = tw[tw.season == 2026].week.max()
    d = tw[(tw.season == 2026) & (tw.week == last)].merge(
        r[(r.season == 2026) & (r.week == last)][["team", "strength_rank"]], on="team")
    d = d[d.next_rank.notna() | (d.strength_rank <= 25)]
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot([1, 30], [1, 30], color=AXIS, lw=1, zorder=1)
    for _, row in d.iterrows():
        x = row.strength_rank if row.strength_rank <= 30 else 30
        y = row.next_rank if pd.notna(row.next_rank) else 27
        color = CONF_COLOR[row.conf_group] if row.conf_group in ("SEC", "ACC") else GRAY_MID
        ax.plot(x, y, "o", ms=8, color=color, mec=SURFACE, mew=1.5, zorder=3)
        if row.conf_group in ("SEC", "ACC") or abs(x - y) >= 8:
            ax.annotate(row.team, (x, y), xytext=(5, 2), textcoords="offset points", fontsize=7, color=INK2)
    for c in ("SEC", "ACC"):
        ax.plot([], [], "o", color=CONF_COLOR[c], label=c)
    ax.plot([], [], "o", color=GRAY_MID, label="Other conferences")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
    ax.set_xlim(0, 31)
    ax.set_ylim(28, 0)
    ax.set_yticks([1, 5, 10, 15, 20, 25, 27])
    ax.set_yticklabels(["1", "5", "10", "15", "20", "25", "unranked"])
    ax.set_xticks([1, 5, 10, 15, 20, 25, 30])
    ax.set_xticklabels(["1", "5", "10", "15", "20", "25", "30+"])
    ax.set_xlabel(f"Season-only rating rank after week {last}")
    ax.set_ylabel(f"AP rank, poll {last + 1}")
    ax.set_title("2026 so far: AP poll vs this season's results")
    save(fig, "fig20_2026_poll_vs_rating.png",
         "Above the diagonal: ranked higher by AP than by results. Ratings below 30th shown at 30+. "
         "Early-season ratings are noisy.")


def fig_h5_sensitivity():
    h = load("h5_sensitivity.json")["final_poll_corrected"]
    labels = {"A": "A. As published", "B": "B. Shape matched (fairest test)",
              "C": "C. Timing matched", "D": "D. Shape and timing matched"}
    series = [("SEC", SEC, -0.22), ("ACC", ACC, 0.0), ("SEC minus ACC", INK, 0.22)]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    for i, v in enumerate("ABCD"):
        for name, color, off in series:
            if name == "SEC minus ACC":
                m, (lo, hi) = h[v]["sec_minus_acc"], h[v]["sec_minus_acc_ci"]
            else:
                m, (lo, hi) = h[v][name]["mean"], h[v][name]["ci"]
            y = i + off
            ax.plot([lo, hi], [y, y], color=color, lw=2)
            dot(ax, m, y, color, size=8, zorder=3)
            ax.annotate(f"{m:+.1f}", (hi, y), xytext=(5, 0), textcoords="offset points",
                        va="center", fontsize=8, color=INK2)
    ax.axvline(0, color=AXIS, lw=1)
    ax.axhspan(0.6, 1.4, color="#f0efec", lw=0, zorder=0)
    ax.set_yticks(range(4))
    ax.set_yticklabels([labels[v] for v in "ABCD"])
    ax.set_ylim(3.6, -0.6)
    ax.grid(axis="y", visible=False)
    for name, color, _ in series:
        ax.plot([], [], "o", color=color, label=name)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3)
    ax.set_xlabel("Schedule inflation (rank places; + = poll makes schedules look tougher)")
    ax.set_title("H5 sensitivity: most of the SEC-ACC gap is a measurement artifact")
    save(fig, "fig21_h5_sensitivity.png",
         "2014-2025, 95% intervals. B compares game-day poll standing with final results on the same "
         "top-25 scale: the SEC effect (+5.7) remains, the ACC effect and the SEC-ACC gap do not.")


def fig_2026_board():
    d = pd.read_csv(RES / "rankings_2026.csv")
    d = d.sort_values(["ap_rank", "results_rank"], na_position="last").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9, 9))
    for i, row in d.iterrows():
        ap = row.ap_rank if pd.notna(row.ap_rank) else 26
        res = min(row.results_rank, 41)
        color = SEC if row.conference == "SEC" else ACC if row.conference == "ACC" else GRAY_MID
        ax.plot([ap, res], [i, i], color=GRID, lw=3, zorder=1)
        ax.plot(ap, i, "o", ms=9, color=color, mec=SURFACE, mew=1.5, zorder=3)
        ax.plot(res, i, "o", ms=8, mfc=SURFACE, mec=color, mew=2, zorder=3)
        if row.verdict in ("overrated", "underrated"):
            ax.annotate(row.verdict, (max(ap, res), i), xytext=(10, 0), textcoords="offset points",
                        va="center", fontsize=8, color=INK, fontweight="bold")
    labels = [f"{t} ({r})" for t, r in zip(d.team, d.record)]
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_ylim(len(d) - 0.4, -0.6)
    ax.set_xlim(0, 46)
    ax.set_xticks([1, 5, 10, 15, 20, 26, 30, 35, 40])
    ax.set_xticklabels(["1", "5", "10", "15", "20", "unranked", "30", "35", "40+"])
    ax.grid(axis="y", visible=False)
    ax.plot([], [], "o", color=GRAY_DARK, label="AP poll rank")
    ax.plot([], [], "o", mfc=SURFACE, mec=GRAY_DARK, mew=2, label="rank by 2026 results")
    ax.plot([], [], "s", color=SEC, label="SEC")
    ax.plot([], [], "s", color=ACC, label="ACC")
    ax.plot([], [], "s", color=GRAY_MID, label="other")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=5, fontsize=8)
    ax.set_title("2026 after week 7: AP poll vs this season's results")
    save(fig, "fig22_2026_over_under.png",
         "Exploratory. Labelled only when the voter-model lens agrees and the gap is 5+ places. "
         "Unranked teams shown at 26 (their true poll spot is 26 or lower).\n"
         "Seven weeks of games: ratings are noisy and see only scores, not injuries or quarterback changes.")


def fig_t1():
    t = load("preseason_tests.json")["T1_preseason_vs_results"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 3.8), gridspec_kw={"width_ratios": [1.3, 1]})
    fig.subplots_adjust(wspace=0.55)
    rows = [(f"{CONF_LABEL.get(c, c)} (n={t[c]['preseason_ranked_team_seasons']})",
             t[c]["adjusted_shortfall"], *t[c]["adjusted_ci"], CONF_COLOR[c]) for c in CONFS]
    rows.append(("SEC minus ACC", t["sec_minus_acc"], *t["sec_minus_acc_ci"], INK))
    forest(a1, rows, "Finished below their preseason rank, vs typical",
           "Places below expectation for that preseason rank")
    y = np.arange(len(CONFS))
    vals = [t[c]["share_finished_outside_results_top25"] * 100 for c in CONFS]
    a2.barh(y, vals, height=0.5, color=[CONF_COLOR[c] for c in CONFS])
    for i, v in enumerate(vals):
        a2.annotate(f"{v:.0f}%", (v, i), xytext=(4, 0), textcoords="offset points", va="center", fontsize=9)
    a2.set_yticks(y)
    a2.set_yticklabels([CONF_LABEL.get(c, c) for c in CONFS])
    a2.invert_yaxis()
    a2.set_xlim(0, 75)
    a2.grid(axis="y", visible=False)
    a2.set_xlabel("Preseason-ranked teams outside the results top 25 at season's end (%)")
    a2.set_title("Preseason picks that did not hold up")
    save(fig, "fig23_t1_preseason_vs_results.png",
         "T1, 2014-2025. Adjusted for what is typical at each preseason rank (higher-ranked teams have further to fall). "
         "SEC preseason rankings hold up as well as anyone's.")


def fig_t2():
    t = load("preseason_tests.json")["T2_schedule_boost_by_week"]
    bands = ["early (weeks 1-4)", "middle (weeks 5-8)", "late (weeks 9+)"]
    fig, ax = plt.subplots(figsize=(8.5, 4))
    x = np.arange(len(bands))
    for c, off in (("SEC", -0.12), ("ACC", 0.0), ("Big Ten", 0.12)):
        color = CONF_COLOR[c] if c != "Big Ten" else GRAY_MID
        m = [t[c][b]["mean_gap"] for b in bands]
        lo = [t[c][b]["ci"][0] for b in bands]
        hi = [t[c][b]["ci"][1] for b in bands]
        for xi, mi, l, h in zip(x + off, m, lo, hi):
            ax.plot([xi, xi], [l, h], color=color, lw=2)
            dot(ax, xi, mi, color, size=8, zorder=3)
        ax.plot(x + off, m, color=color, lw=1, alpha=0.5)
        ax.plot([], [], "o", color=color, label=c)
    ax.axhline(0, color=AXIS, lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(["Weeks 1-4", "Weeks 5-8", "Weeks 9+"])
    ax.set_ylabel("Opponent's game-day rank points\nminus final rank points, per game")
    ax.legend(loc="upper right", ncol=3)
    ax.grid(axis="x", visible=False)
    ax.set_title("SEC opponents look better than they finish, all season long")
    save(fig, "fig24_t2_schedule_boost_by_week.png",
         "T2, 2014-2025, 95% intervals. One rank point = one place inside the top 25. "
         "The SEC gap is not concentrated early, so no preseason link is shown; it exceeds the ACC's in every band.")


def main():
    for f in (fig_timeline, fig_data_overview, fig_training_mae, fig_replay_training, fig_climbers,
              fig_holdout, fig_holdout_scatter, fig_rating_validation, fig_elo_carryover,
              fig_poll_vs_strength, fig_poll_vs_strength_counts, fig_carryover, fig_conference_effect,
              fig_rewards, fig_schedule_inflation, fig_head_start, fig_base_rates,
              fig_counterfactual_slots, fig_counterfactual_teams, fig_2026_now, fig_h5_sensitivity,
              fig_2026_board, fig_t1, fig_t2):
        f()
    print(f"Wrote {len(list(FIG.glob('*.png')))} figures to {FIG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
