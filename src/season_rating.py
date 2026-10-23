"""Season-only strength rating (DEVIATIONS.md, 2026-10-23). Offline only.

Each week, from that season's games only (every team starts equal):
  results     Colley method: wins/losses, with opponents' (and their opponents')
              results entering through one joint solve
  performance margin-based least squares: capped margin = r_home - r_away + h*home,
              plus one 0-margin pseudo-game per team against an average opponent
  combined    50/50 average of the two, each standardized across FBS teams

Writes data/processed/season_ratings.csv (rating after week w's games, one row per
FBS team per week, plus the pooled FCS team on the FBS scale) and results/season_rating_validation.json (next-week winner
picks vs Elo and the AP poll).
"""

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd

from build_features import load_games, load_polls

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed" / "season_ratings.csv"
VALID = ROOT / "results" / "season_rating_validation.json"
SEASONS = [s for s in range(2014, 2027) if s != 2020]
MARGIN_CAP = 28
FCS = "FCS (pooled)"
FIRST_PREDICTED_WEEK = 6


def season_games(season):
    with redirect_stdout(io.StringIO()):
        g = load_games(season)
    fbs = set(g.home_team[g.home_division == "fbs"]) | set(g.away_team[g.away_division == "fbs"])
    g = g.assign(
        home=np.where(g.home_division == "fbs", g.home_team, FCS),
        away=np.where(g.away_division == "fbs", g.away_team, FCS),
        margin=(g.home_points - g.away_points).astype(float))
    return g, sorted(fbs)


def colley(games, teams):
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    C = 2 * np.eye(n)
    b = np.ones(n)
    for h, a, m in zip(games.home, games.away, games.margin):
        i, j = idx[h], idx[a]
        C[i, i] += 1
        C[j, j] += 1
        C[i, j] -= 1
        C[j, i] -= 1
        if m > 0:
            b[i] += 0.5
            b[j] -= 0.5
        elif m < 0:
            b[i] -= 0.5
            b[j] += 0.5
    return pd.Series(np.linalg.solve(C, b), index=teams)


def performance(games, teams):
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    rows, y = [], []
    for h, a, m, neutral in zip(games.home, games.away, games.margin, games.neutral_site):
        x = np.zeros(n + 1)
        x[idx[h]], x[idx[a]], x[n] = 1, -1, 0 if neutral else 1
        rows.append(x)
        y.append(np.clip(m, -MARGIN_CAP, MARGIN_CAP))
    for t in teams:
        x = np.zeros(n + 1)
        x[idx[t]] = 1
        rows.append(x)
        y.append(0.0)
    sol = np.linalg.lstsq(np.array(rows), np.array(y), rcond=None)[0]
    return pd.Series(sol[:n], index=teams), float(sol[n])


def ratings_for_season(season):
    games, fbs = season_games(season)
    teams = fbs + [FCS]
    out = []
    for w in sorted(games.week.unique()):
        played = games[games.week <= w]
        res = colley(played, teams)
        perf, home_edge = performance(played, teams)
        # Standardize with FBS teams only; the pooled FCS team is scored on the same scale.
        combined = (0.5 * (res - res[fbs].mean()) / res[fbs].std()
                    + 0.5 * (perf - perf[fbs].mean()) / perf[fbs].std())
        rank = combined[fbs].rank(ascending=False, method="min").reindex(teams)
        out.append(pd.DataFrame({
            "season": season, "week": w, "team": teams,
            "results_rating": res.values, "performance_rating": perf.values,
            "home_edge": home_edge, "combined": combined.values,
            "strength_rank": rank.values}))
    return games, pd.concat(out, ignore_index=True)


def validate(games, ratings, season):
    """Next-week winner picks: rating through week w -> games of week w+1."""
    polls, _ = load_polls(season)
    picks = []
    fbs_games = games[(games.home_division == "fbs") & (games.away_division == "fbs")
                      & (games.margin != 0)]
    for w in sorted(fbs_games.week.unique()):
        if w < FIRST_PREDICTED_WEEK or w - 1 not in set(ratings.week):
            continue
        r = ratings[ratings.week == w - 1].set_index("team")
        poll = polls.get(w, {})
        for _, g in fbs_games[fbs_games.week == w].iterrows():
            h, a = g.home_team, g.away_team
            home_won = g.margin > 0
            hr, ar = poll.get(h, (None,))[0], poll.get(a, (None,))[0]
            if hr is None and ar is None:
                ap = None
            else:
                ap = (hr if hr is not None else 99) < (ar if ar is not None else 99)
            picks.append({
                "combined": (r.combined[h] > r.combined[a]) == home_won,
                "results": (r.results_rating[h] > r.results_rating[a]) == home_won,
                "performance": (r.performance_rating[h] - r.performance_rating[a]
                                + (0 if g.neutral_site else r.home_edge.iloc[0]) > 0) == home_won,
                "elo": (g.home_pregame_elo > g.away_pregame_elo) == home_won
                       if pd.notna(g.home_pregame_elo) and pd.notna(g.away_pregame_elo) else None,
                "ap": None if ap is None else ap == home_won,
            })
    return pd.DataFrame(picks)


def main():
    all_ratings, all_picks = [], []
    for season in SEASONS:
        games, ratings = ratings_for_season(season)
        all_ratings.append(ratings)
        if season <= 2025:
            all_picks.append(validate(games, ratings, season))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.concat(all_ratings).to_csv(OUT, index=False)

    p = pd.concat(all_picks, ignore_index=True)
    both = p.dropna(subset=["elo"])
    with_ap = both.dropna(subset=["ap"])
    report = {
        "games_all": int(len(both)),
        "accuracy_all_games": {m: float(both[m].astype(bool).mean())
                               for m in ("combined", "results", "performance", "elo")},
        "games_with_a_ranked_team": int(len(with_ap)),
        "accuracy_games_with_a_ranked_team": {
            m: float(with_ap[m].astype(bool).mean())
            for m in ("combined", "results", "performance", "elo", "ap")},
        "note": (f"Winners of FBS-vs-FBS games in week {FIRST_PREDICTED_WEEK}+ of 2014-2025 "
                 "regular seasons, picked from ratings through the previous week (Elo: "
                 "pregame Elo; AP: better-ranked team in the poll before the game)."),
    }
    VALID.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Next-week winner picks, {report['games_all']} games:",
          {k: f"{v:.1%}" for k, v in report["accuracy_all_games"].items()})
    print(f"Games with a ranked team ({report['games_with_a_ranked_team']}):",
          {k: f"{v:.1%}" for k, v in report["accuracy_games_with_a_ranked_team"].items()})


if __name__ == "__main__":
    main()
