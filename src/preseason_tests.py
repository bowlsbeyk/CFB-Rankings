"""Two tests of the preseason link (DEVIATIONS.md, 2026-10-23; added after earlier results).

T1  Are SEC preseason rankings unjustified? Preseason AP rank vs final season-only
    rank (capped at 26), adjusted for what is typical at each preseason rank.
T2  Does the SEC's schedule boost come from early-season rankings? Per-game gap between
    an opponent's game-day AP rank points and its final season-only rank points, by
    part of the season.

95% intervals: 1,000 resamples of team-seasons (seed 0). Writes results/preseason_tests.json.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
RATINGS = ROOT / "data" / "processed" / "season_ratings.csv"
OUT = ROOT / "results" / "preseason_tests.json"
SEASONS = [s for s in range(2014, 2026) if s != 2020]
CONFS = ["SEC", "ACC", "Big Ten", "Big 12", "Other"]
BANDS = {"early (weeks 1-4)": (1, 4), "middle (weeks 5-8)": (5, 8), "late (weeks 9+)": (9, 99)}
N_BOOT = 1000


def rank_points(rank):
    return np.where(pd.notna(rank) & (rank <= 25), 26 - rank, 0.0)


def ci(x):
    return [float(v) for v in np.percentile(x, [2.5, 97.5])]


def final_ranks(ratings):
    last = ratings.groupby("season").week.transform("max") == ratings.week
    return ratings[last].set_index(["season", "team"]).strength_rank


def t1(tw, ratings, rng):
    final = final_ranks(ratings)
    pre = tw[tw.week == 1].dropna(subset=["prior_rank"])[["season", "team", "conf_group", "prior_rank"]].copy()
    pre["final_rank"] = [final.get((s, t), np.nan) for s, t in zip(pre.season, pre.team)]
    pre["final_capped"] = pre.final_rank.clip(upper=26)
    pre["shortfall"] = pre.final_capped - pre.prior_rank
    slope, intercept = np.polyfit(pre.prior_rank, pre.shortfall, 1)
    pre["adjusted"] = pre.shortfall - (intercept + slope * pre.prior_rank)
    pre["outside_top25"] = (pre.final_rank > 25).astype(float)

    out = {"team_seasons": int(len(pre)),
           "expected_shortfall_fit": {"intercept": float(intercept), "slope": float(slope)}}
    boots = {}
    for c in CONFS:
        g = pre[pre.conf_group == c]
        idx = rng.integers(0, len(g), size=(N_BOOT, len(g)))
        boots[c] = g.adjusted.to_numpy()[idx].mean(1)
        out[c] = {"preseason_ranked_team_seasons": int(len(g)),
                  "adjusted_shortfall": float(g.adjusted.mean()), "adjusted_ci": ci(boots[c]),
                  "raw_shortfall": float(g.shortfall.mean()),
                  "share_finished_outside_results_top25": float(g.outside_top25.mean()),
                  "mean_preseason_rank": float(g.prior_rank.mean())}
    d = boots["SEC"] - boots["ACC"]
    out["sec_minus_acc"] = float(out["SEC"]["adjusted_shortfall"] - out["ACC"]["adjusted_shortfall"])
    out["sec_minus_acc_ci"] = ci(d)
    sec = out["SEC"]
    sec_pos = sec["adjusted_ci"][0] > 0
    gap_pos = out["sec_minus_acc_ci"][0] > 0
    out["reading"] = ("supports" if sec_pos and gap_pos else "partial" if sec_pos
                      else "refutes" if sec["adjusted_shortfall"] <= 0 else "inconclusive")
    out["note"] = ("Shortfall = final season-only rank (capped at 26) - preseason AP rank; adjusted = "
                   "shortfall minus the all-conference straight-line expectation at that preseason rank. "
                   "Positive = finished below where the preseason poll put the team.")
    return out, pre


def t2(tw, ratings, rng):
    final = final_ranks(ratings)
    game_pts = pd.Series(rank_points(tw.prior_rank.to_numpy()), index=[tw.season, tw.week, tw.team])
    fin_pts = pd.Series(rank_points(final.to_numpy()), index=final.index)
    rows = []
    for _, r in tw[tw.season.isin(SEASONS) & (tw.games > 0)].iterrows():
        for o in r.opponents.split(";"):
            rows.append((r.season, r.team, r.conf_group, r.week,
                         game_pts.get((r.season, r.week, o), 0.0) - fin_pts.get((r.season, o), 0.0)))
    g = pd.DataFrame(rows, columns=["season", "team", "conf_group", "week", "gap"])
    g["band"] = pd.cut(g.week, [0, 4, 8, 99], labels=list(BANDS))

    out = {"games": int(len(g)),
           "note": ("Per game: opponent's AP rank points in the poll before the game minus its final "
                    "season-only rank points (26 - rank inside the top 25, else 0). Positive = the "
                    "opponent looked better on game day than its season ended up.")}
    boot_means = {}
    for c in CONFS:
        gc = g[g.conf_group == c]
        ts = gc.groupby(["season", "team"])
        units = list(ts.groups)
        sums = np.zeros((len(units), len(BANDS)))
        cnts = np.zeros((len(units), len(BANDS)))
        pos = {u: i for i, u in enumerate(units)}
        for (s, t, b), sub in gc.groupby(["season", "team", "band"], observed=True).gap:
            j = list(BANDS).index(b)
            sums[pos[(s, t)], j] = sub.sum()
            cnts[pos[(s, t)], j] = len(sub)
        idx = rng.integers(0, len(units), size=(N_BOOT, len(units)))
        bm = sums[idx].sum(1) / cnts[idx].sum(1)
        boot_means[c] = bm
        point = sums.sum(0) / cnts.sum(0)
        out[c] = {b: {"mean_gap": float(point[j]), "ci": ci(bm[:, j]), "games": int(cnts[:, j].sum())}
                  for j, b in enumerate(BANDS)}
        out[c]["early_minus_late"] = float(point[0] - point[2])
        out[c]["early_minus_late_ci"] = ci(bm[:, 0] - bm[:, 2])
    out["sec_minus_acc"] = {b: {"diff": float(out["SEC"][b]["mean_gap"] - out["ACC"][b]["mean_gap"]),
                                "ci": ci(boot_means["SEC"][:, j] - boot_means["ACC"][:, j])}
                            for j, b in enumerate(BANDS)}
    early = out["SEC"]["early (weeks 1-4)"]
    out["reading"] = ("supports preseason link" if early["ci"][0] > 0 and out["SEC"]["early_minus_late_ci"][0] > 0
                      else "no link shown")
    return out


def main():
    tw = pd.read_csv(TABLE)
    tw = tw[tw.season.isin(SEASONS)]
    ratings = pd.read_csv(RATINGS)
    r1, _ = t1(tw, ratings, np.random.default_rng(0))
    r2 = t2(tw, ratings, np.random.default_rng(0))
    OUT.write_text(json.dumps({"T1_preseason_vs_results": r1, "T2_schedule_boost_by_week": r2}, indent=2) + "\n")

    print(f"T1 ({r1['team_seasons']} preseason-ranked team-seasons): reading = {r1['reading']}")
    for c in CONFS:
        x = r1[c]
        print(f"  {c:8} n={x['preseason_ranked_team_seasons']:3}  adjusted {x['adjusted_shortfall']:+.2f} "
              f"({x['adjusted_ci'][0]:+.2f}, {x['adjusted_ci'][1]:+.2f})  raw {x['raw_shortfall']:+.2f}  "
              f"outside results top 25 {x['share_finished_outside_results_top25']:.0%}  "
              f"avg preseason rank {x['mean_preseason_rank']:.1f}")
    print(f"  SEC-ACC {r1['sec_minus_acc']:+.2f} ({r1['sec_minus_acc_ci'][0]:+.2f}, {r1['sec_minus_acc_ci'][1]:+.2f})")
    print(f"T2 ({r2['games']} games): reading = {r2['reading']}")
    for c in CONFS:
        x = r2[c]
        print(f"  {c:8} " + "  ".join(f"{b.split()[0]} {x[b]['mean_gap']:+.2f} ({x[b]['ci'][0]:+.2f}, {x[b]['ci'][1]:+.2f})"
                                     for b in BANDS)
              + f"  early-late {x['early_minus_late']:+.2f} ({x['early_minus_late_ci'][0]:+.2f}, {x['early_minus_late_ci'][1]:+.2f})")
    print("  SEC-ACC " + "  ".join(f"{b.split()[0]} {v['diff']:+.2f} ({v['ci'][0]:+.2f}, {v['ci'][1]:+.2f})"
                                   for b, v in r2["sec_minus_acc"].items()))


if __name__ == "__main__":
    main()
