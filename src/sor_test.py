"""T5: is the SEC ranked so high because of its results? (DEVIATIONS.md, 2026-10-31.)

Ranking-independent measures, built only from the current season's scores and who
played whom (no polls, no preseason, no prior season, no names or conference labels):
  performance   the season-only performance rating (margin-based), after week w
  SOR           strength of record: the probability that a benchmark team (the average
                of the 25 best teams by performance that week) would win at least as many
                of a team's games as it did, against the same opponents at the same
                venues. Lower = more impressive record.

Compares how many top-25 slots each conference gets from the AP poll with how many it
gets from SOR and from performance, 2014-2025 and 2026 to date.

Writes data/processed/sor.csv, results/t5_sor.json and results/sor_2026.csv.
"""

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from build_features import load_games

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
RATINGS = ROOT / "data" / "processed" / "season_ratings.csv"
SOR_TABLE = ROOT / "data" / "processed" / "sor.csv"
OUT = ROOT / "results" / "t5_sor.json"
OUT_2026 = ROOT / "results" / "sor_2026.csv"
HIST = [s for s in range(2014, 2026) if s != 2020]
SEASONS = HIST + [2026]
CONFS = ["SEC", "ACC", "Big Ten", "Big 12", "Other"]
FCS = "FCS (pooled)"
FIRST_WEEK = 5
N_BOOT = 1000


def season_games(season):
    with redirect_stdout(io.StringIO()):
        g = load_games(season)
    g = g.assign(home=np.where(g.home_division == "fbs", g.home_team, FCS),
                 away=np.where(g.away_division == "fbs", g.away_team, FCS),
                 margin=(g.home_points - g.away_points).astype(float))
    return g


def estimate_sigma(ratings):
    """SD of (actual margin - pre-game predicted margin), FBS vs FBS, weeks 4+, 2014-2025."""
    r = ratings.set_index(["season", "week", "team"])
    errs = []
    for season in HIST:
        g = season_games(season)
        g = g[(g.home != FCS) & (g.away != FCS) & (g.week >= 4)]
        for _, x in g.iterrows():
            try:
                h, a = r.loc[(season, x.week - 1, x.home)], r.loc[(season, x.week - 1, x.away)]
            except KeyError:
                continue
            pred = h.performance_rating - a.performance_rating + (0 if x.neutral_site else h.home_edge)
            errs.append(x.margin - pred)
    return float(np.std(errs)), len(errs)


def at_least(probs, k):
    """P(at least k successes) for independent trials with the given probabilities."""
    dist = np.zeros(len(probs) + 1)
    dist[0] = 1.0
    for p in probs:
        dist[1:] = dist[1:] * (1 - p) + dist[:-1] * p
        dist[0] *= 1 - p
    return float(dist[k:].sum())


def sor_table(ratings, sigma):
    rows = []
    for season in SEASONS:
        g = season_games(season)
        rs = ratings[ratings.season == season]
        for w in sorted(rs.week.unique()):
            rw = rs[rs.week == w].set_index("team")
            perf = rw.performance_rating
            fbs = [t for t in rw.index if t != FCS]
            bench = perf[fbs].nlargest(25).mean()
            h = rw.home_edge.iloc[0]
            played = g[g.week <= w]
            for t in fbs:
                mine = played[(played.home == t) | (played.away == t)]
                probs, wins = [], 0
                for _, x in mine.iterrows():
                    at_home = x.home == t
                    opp = x.away if at_home else x.home
                    v = 0 if x.neutral_site else (1 if at_home else -1)
                    probs.append(norm.cdf((bench - perf[opp] + h * v) / sigma))
                    wins += int((x.margin > 0) if at_home else (x.margin < 0))
                rows.append({"season": season, "week": int(w), "team": t, "games": len(probs),
                             "wins": wins, "losses": len(probs) - wins,
                             "sor_prob": at_least(probs, wins) if probs else 1.0,
                             "performance_rating": float(perf[t])})
    d = pd.DataFrame(rows)
    grp = d.groupby(["season", "week"])
    d["sor_rank"] = grp.sor_prob.rank(method="min")
    d["perf_rank"] = grp.performance_rating.rank(ascending=False, method="min")
    return d


def main():
    ratings = pd.read_csv(RATINGS)
    sigma, n_sigma = estimate_sigma(ratings)
    sor = sor_table(ratings, sigma)
    SOR_TABLE.parent.mkdir(parents=True, exist_ok=True)
    sor.to_csv(SOR_TABLE, index=False)
    print(f"sigma = {sigma:.2f} points from {n_sigma} games; SOR rows: {len(sor)}")


if __name__ == "__main__":
    main()
