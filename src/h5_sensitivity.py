"""H5 sensitivity: schedule inflation with shape and timing matched (DEVIATIONS.md,
2026-10-23, added after seeing H5 results).

Each FBS team-season's schedule is scored two ways and ranked among FBS teams
(average ranks for ties); inflation = rating-side rank - poll-side rank (positive =
the poll makes the schedule look tougher). Variants:

  A  as published   poll: AP points per voter before each game | rating: final rating
  B  shape matched  poll: AP rank points before each game      | rating: final rank points
  C  timing matched poll: final AP points per voter            | rating: final rating
  D  both matched   poll: final AP rank points                 | rating: final rank points

Rank points = 26 - rank inside the top 25, else 0. FCS opponents score 0 on the poll
side, the pooled FCS rating on the continuous rating side and 0 as rank points.
The final regular-season poll is the poll after each season's last schedule week;
the review's lookup (one poll earlier) is also computed to check its table.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from bias_tests import CONFS, FCS, group_means

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
RATINGS = ROOT / "data" / "processed" / "season_ratings.csv"
OUT = ROOT / "results" / "h5_sensitivity.json"
SEASONS = [s for s in range(2014, 2026) if s != 2020]
VARIANTS = {
    "A": "As published: poll before game (points per voter) vs final rating",
    "B": "Shape matched: poll before game vs final rating, both as top-25 rank points",
    "C": "Timing matched: final poll (points per voter) vs final rating",
    "D": "Shape and timing matched: final poll vs final rating, both as top-25 rank points",
}


def rank_points(rank):
    return np.where(pd.notna(rank) & (rank <= 25), 26 - rank, 0.0)


def lookups(tw, ratings, final_poll):
    """Opponent value tables keyed by (season, week, team) or (season, team)."""
    g = tw.set_index(["season", "week", "team"])
    game_ppv = g.prior_ppv_zero
    game_pts = pd.Series(rank_points(g.prior_rank.to_numpy()), index=g.index)

    last = tw[tw.week == tw.groupby("season").week.transform("max")].set_index(["season", "team"])
    if final_poll == "corrected":
        fin_ppv, fin_rank = last.next_ppv_zero, last.next_rank
    else:
        fin_ppv, fin_rank = last.prior_ppv_zero, last.prior_rank
    fin_pts = pd.Series(rank_points(fin_rank.to_numpy()), index=last.index)

    r = ratings[ratings.week == ratings.groupby("season").week.transform("max")]
    r = r.set_index(["season", "team"])
    rating = r.combined
    rating_pts = pd.Series(rank_points(r.strength_rank.to_numpy()), index=r.index)
    return game_ppv, game_pts, fin_ppv, fin_pts, rating, rating_pts


def schedules(tw, ratings, final_poll):
    game_ppv, game_pts, fin_ppv, fin_pts, rating, rating_pts = lookups(tw, ratings, final_poll)
    rows = []
    played = tw[tw.season.isin(SEASONS) & (tw.games > 0)]
    for (season, team), g in played.groupby(["season", "team"]):
        vals = {k: [] for k in ("A_poll", "B_poll", "C_poll", "D_poll", "rating", "rating_pts")}
        for week, opps in zip(g.week, g.opponents):
            for o in opps.split(";"):
                vals["A_poll"].append(game_ppv.get((season, week, o), 0.0))
                vals["B_poll"].append(game_pts.get((season, week, o), 0.0))
                vals["C_poll"].append(fin_ppv.get((season, o), 0.0))
                vals["D_poll"].append(fin_pts.get((season, o), 0.0))
                vals["rating"].append(rating.get((season, o), rating[(season, FCS)]))
                vals["rating_pts"].append(rating_pts.get((season, o), 0.0))
        rows.append({"season": season, "team": team, "conf_group": g.conf_group.iloc[0],
                     **{k: float(np.mean(v)) for k, v in vals.items()}})
    s = pd.DataFrame(rows)

    def rk(col):
        return s.groupby("season")[col].rank(ascending=False, method="average")

    for v, (poll_col, rating_col) in {"A": ("A_poll", "rating"), "B": ("B_poll", "rating_pts"),
                                      "C": ("C_poll", "rating"), "D": ("D_poll", "rating_pts")}.items():
        s[f"inflation_{v}"] = rk(rating_col) - rk(poll_col)
    return s


def summarize(s):
    out = {}
    for v in VARIANTS:
        block = group_means(s, f"inflation_{v}", np.random.default_rng(0))
        out[v] = {"description": VARIANTS[v],
                  **{c: {"mean": block[c]["mean"], "ci": block[c]["ci"], "team_seasons": block[c]["team_seasons"]}
                     for c in CONFS},
                  "sec_minus_acc": block["sec_minus_acc"], "sec_minus_acc_ci": block["sec_minus_acc_ci"]}
    return out


def main():
    tw = pd.read_csv(TABLE)
    ratings = pd.read_csv(RATINGS)
    report = {
        "final_poll_corrected": summarize(schedules(tw, ratings, "corrected")),
        "final_poll_review_lookup": summarize(schedules(tw, ratings, "review")),
        "note": ("Rank places among FBS teams, 2014-2025 (no 2020); positive = the poll makes the "
                 "schedule look tougher than results. Reported result: final_poll_corrected (final "
                 "poll = poll after the last schedule week). final_poll_review_lookup uses the "
                 "review's approximation (one poll earlier) to check its table. A and B do not use "
                 "the final poll, so they are identical in both."),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    for key in ("final_poll_corrected", "final_poll_review_lookup"):
        print(key)
        for v, b in report[key].items():
            print(f"  {v}  SEC {b['SEC']['mean']:+.1f} ({b['SEC']['ci'][0]:+.1f}, {b['SEC']['ci'][1]:+.1f})"
                  f"  ACC {b['ACC']['mean']:+.1f} ({b['ACC']['ci'][0]:+.1f}, {b['ACC']['ci'][1]:+.1f})"
                  f"  SEC-ACC {b['sec_minus_acc']:+.1f} ({b['sec_minus_acc_ci'][0]:+.1f}, "
                  f"{b['sec_minus_acc_ci'][1]:+.1f})")


if __name__ == "__main__":
    main()
