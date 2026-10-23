"""T4: does the season-only rating overrate the SEC? (DEVIATIONS.md, 2026-10-23; added
after earlier results.)

Referees the rating with games between a conference's teams and FBS outsiders: regular
season from week 4 on, plus all postseason games (which the rating never saw). The
prediction is made before each game from the performance component (margin scale):
team rating - opponent rating + home edge. Measure: mean of (actual margin, capped at
+/-28, - predicted margin). Negative = the conference does worse against outsiders than
the rating expects, i.e. the rating overrates it.

95% intervals: 1,000 resamples of team-seasons (seed 0). Writes results/t4_referee.json
and every game to results/t4_referee_games.csv.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "schedules"
RATINGS = ROOT / "data" / "processed" / "season_ratings.csv"
OUT = ROOT / "results" / "t4_referee.json"
GAMES = ROOT / "results" / "t4_referee_games.csv"
SEASONS = [s for s in range(2014, 2026) if s != 2020]
CONFS = ["SEC", "ACC", "Big Ten", "Big 12", "Pac-12"]
FIRST_WEEK = 4
CAP = 28
N_BOOT = 1000


def is_power(conf, team, season):
    return (conf in ("SEC", "ACC", "Big Ten", "Big 12") or (conf == "Pac-12" and season <= 2023)
            or team == "Notre Dame")


def load_games():
    frames = []
    for season in SEASONS:
        s = pd.read_parquet(RAW / f"cfb_schedules_{season}.parquet")
        s = s[s.completed & (s.home_division == "fbs") & (s.away_division == "fbs")
              & (s.home_conference != s.away_conference)]
        frames.append(s)
    return pd.concat(frames, ignore_index=True)


def side_rows(games, ratings):
    """One row per (conference team, outsider) game, from the conference team's side."""
    r = ratings.set_index(["season", "week", "team"])
    last_week = ratings.groupby("season").week.max()
    rows = []
    for _, g in games.iterrows():
        post = g.season_type == "postseason"
        if not post and g.week < FIRST_WEEK:
            continue
        rweek = last_week[g.season] if post else g.week - 1
        for side, other in (("home", "away"), ("away", "home")):
            team, opp = g[f"{side}_team"], g[f"{other}_team"]
            try:
                tr = r.loc[(g.season, rweek, team)]
                orr = r.loc[(g.season, rweek, opp)]
            except KeyError:
                continue
            venue = 0 if g.neutral_site else (1 if side == "home" else -1)
            pred = tr.performance_rating - orr.performance_rating + venue * tr.home_edge
            margin = g[f"{side}_points"] - g[f"{other}_points"]
            rows.append({
                "season": g.season, "week": g.week, "season_type": g.season_type,
                "team": team, "conference": g[f"{side}_conference"],
                "opponent": opp, "opp_conference": g[f"{other}_conference"],
                "opp_power": is_power(g[f"{other}_conference"], opp, g.season),
                "venue": {1: "home", -1: "away", 0: "neutral"}[venue],
                "points_for": g[f"{side}_points"], "points_against": g[f"{other}_points"],
                "margin": margin, "predicted_margin": round(float(pred), 2),
                "residual": round(float(np.clip(margin, -CAP, CAP) - pred), 2),
                "won": int(margin > 0), "predicted_win": int(pred > 0),
            })
    return pd.DataFrame(rows)


def summarize(d, rng):
    per = d.groupby(["season", "team"]).residual.agg(["sum", "count"])
    s, n = per["sum"].to_numpy(), per["count"].to_numpy()
    idx = rng.integers(0, len(per), size=(N_BOOT, len(per)))
    b = s[idx].sum(1) / n[idx].sum(1)
    return {"games": int(len(d)), "mean_residual": float(d.residual.mean()),
            "ci": [float(x) for x in np.percentile(b, [2.5, 97.5])],
            "wins": int(d.won.sum()), "predicted_wins": int(d.predicted_win.sum()),
            "win_share": float(d.won.mean())}


def main():
    games = load_games()
    d = side_rows(games, pd.read_csv(RATINGS))
    d = d[d.conference.isin(CONFS)]
    report = {}
    for c in CONFS:
        dc = d[d.conference == c]
        report[c] = {
            "all": summarize(dc, np.random.default_rng(0)),
            "postseason_only": summarize(dc[dc.season_type == "postseason"], np.random.default_rng(0)),
            "vs_power_opponents": summarize(dc[dc.opp_power], np.random.default_rng(0)),
        }
    sec = report["SEC"]["all"]
    report["reading"] = ("supports Kyle's objection (rating overrates SEC)" if sec["ci"][1] < 0
                         else "refutes it (rating does not overrate SEC)" if sec["ci"][0] > 0
                         else "inconclusive")

    h = games[((games.home_conference == "SEC") & (games.away_conference == "ACC"))
              | ((games.home_conference == "ACC") & (games.away_conference == "SEC"))]
    sec_margin = np.where(h.home_conference == "SEC", h.home_points - h.away_points,
                          h.away_points - h.home_points)
    report["head_to_head_SEC_vs_ACC"] = {
        "games": int(len(h)), "sec_wins": int((sec_margin > 0).sum()), "acc_wins": int((sec_margin < 0).sum()),
        "mean_sec_margin": float(sec_margin.mean()),
        "postseason_games": int((h.season_type == "postseason").sum()),
        "postseason_sec_wins": int(((sec_margin > 0) & (h.season_type == "postseason").to_numpy()).sum()),
        "note": "Raw results, no model; regular season (all weeks) plus postseason, 2014-2025 (no 2020).",
    }
    report["note"] = ("residual = actual margin (capped at +/-28) - margin predicted before the game by the "
                      "season-only rating's performance component. Negative = the conference does worse "
                      "against outsiders than the rating expects (the rating overrates it).")
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    d.sort_values(["season", "week", "team"]).to_csv(GAMES, index=False)

    print(f"T4 reading: {report['reading']}")
    for c in CONFS:
        for k in ("all", "postseason_only", "vs_power_opponents"):
            x = report[c][k]
            print(f"  {c:8} {k:19} n={x['games']:4} residual {x['mean_residual']:+.2f} "
                  f"({x['ci'][0]:+.2f}, {x['ci'][1]:+.2f})  won {x['wins']} of {x['games']} "
                  f"(predicted {x['predicted_wins']})")
    hh = report["head_to_head_SEC_vs_ACC"]
    print(f"Head-to-head SEC vs ACC: {hh['games']} games, SEC {hh['sec_wins']}-{hh['acc_wins']}, "
          f"mean SEC margin {hh['mean_sec_margin']:+.1f}; postseason SEC {hh['postseason_sec_wins']} of "
          f"{hh['postseason_games']}")


if __name__ == "__main__":
    main()
