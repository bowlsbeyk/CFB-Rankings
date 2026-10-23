"""Exploratory: who is over- and underrated in 2026 so far (DEVIATIONS.md, 2026-10-23).

Teams in the latest AP top 25 or the season-only top 25. For each:
  results lens   season-only rating rank minus AP rank (+ = AP ranks the team above its results)
  voter lens     sum over 2026 weeks of (actual - predicted) change in AP points per voter,
                 from the name-blind rated model fit on 2014-2023, in rank places (/0.80)
                 (+ = voters lifted the team more than results usually earn)
  schedules      schedule rank among FBS by opponents' game-day AP rank points vs by
                 opponents' current season-only rank points (H5 variant B scale)

Writes results/rankings_2026.csv and prints the table.
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from train import features

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
RATINGS = ROOT / "data" / "processed" / "season_ratings.csv"
OUT = ROOT / "results" / "rankings_2026.csv"
SEASON = 2026
PPV_PER_PLACE = 0.80
CLEAR = 5


def rank_points(rank):
    return np.where(pd.notna(rank) & (rank <= 25), 26 - rank, 0.0)


def main():
    tw = pd.read_csv(TABLE)
    tw = tw[tw.season == SEASON].copy()
    last = tw.week.max()
    ratings = pd.read_csv(RATINGS)
    r = ratings[(ratings.season == SEASON) & (ratings.week == last)].set_index("team")

    model = joblib.load(ROOT / "results" / "models" / "gbt_rated_zero.joblib")
    tw["pred"] = model.predict(tw[features("zero", "rated")])
    tw["resid"] = tw.target_ppv_zero - tw.pred
    voter = tw.groupby("team").resid.sum() / PPV_PER_PLACE

    game_pts = pd.Series(rank_points(tw.prior_rank.to_numpy()), index=[tw.week, tw.team])
    rating_pts = pd.Series(rank_points(r.strength_rank.to_numpy()), index=r.index)
    sched = []
    for team, g in tw[tw.games > 0].groupby("team"):
        poll_vals, res_vals = [], []
        for week, opps in zip(g.week, g.opponents):
            for o in opps.split(";"):
                poll_vals.append(game_pts.get((week, o), 0.0))
                res_vals.append(rating_pts.get(o, 0.0))
        sched.append({"team": team, "poll_sos": np.mean(poll_vals), "results_sos": np.mean(res_vals)})
    sched = pd.DataFrame(sched).set_index("team")
    sched["schedule_rank_by_poll"] = sched.poll_sos.rank(ascending=False, method="average")
    sched["schedule_rank_by_results"] = sched.results_sos.rank(ascending=False, method="average")

    final = tw[tw.week == last].set_index("team")
    d = pd.DataFrame({
        "conference": final.conference,
        "record": final.wins_to_date.astype(int).astype(str) + "-" + final.losses_to_date.astype(int).astype(str),
        "ap_rank": final.next_rank,
        "results_rank": r.strength_rank.reindex(final.index),
        "voter_lens_places": voter.reindex(final.index).round(1),
        "schedule_rank_by_poll": sched.schedule_rank_by_poll.reindex(final.index),
        "schedule_rank_by_results": sched.schedule_rank_by_results.reindex(final.index),
    })
    d = d[(d.ap_rank <= 25) | (d.results_rank <= 25)].copy()
    # AP-unranked teams count as 26: their true poll position is 26 or lower, so their
    # results-lens value is a lower bound on how far they are underrated.
    d["results_lens_places"] = d.results_rank - d.ap_rank.fillna(26)
    agree = np.sign(d.results_lens_places) == np.sign(d.voter_lens_places)
    d["verdict"] = np.where(agree & (d.results_lens_places >= CLEAR), "overrated",
                            np.where(agree & (d.results_lens_places <= -CLEAR), "underrated", ""))
    d = d.sort_values(["ap_rank", "results_rank"], na_position="last")
    d.index.name = "team"
    d.to_csv(OUT)

    print(f"2026 after week {last} (AP poll {last + 1}); positive = ranked above results / lifted more than usual")
    print(d[["conference", "record", "ap_rank", "results_rank", "results_lens_places", "voter_lens_places",
             "schedule_rank_by_poll", "schedule_rank_by_results", "verdict"]].to_string())


if __name__ == "__main__":
    main()
