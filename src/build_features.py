"""Build the team-week table from the frozen raw files. Offline only.

One row per FBS team per poll transition: schedule week w links AP poll w
(released before week w's games) to AP poll w+1 (released after them).
Week-1 AP poll is the preseason poll.

Points are built under both unranked treatments (see DEVIATIONS.md):
  *_zero   registered rule: outside the top 25 = 0
  *_floor  sensitivity: outside the top 25 = half the lowest-ranked team's points
and in two units: *_points_* (raw AP points, registered) and *_ppv_* (points per
voter, revised; voters = total first-place votes in that poll).
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "team_weeks.csv"

SEASONS = [s for s in range(2014, 2027) if s != 2020]
TREATMENTS = ("zero", "floor")
CONF_GROUPS = {"SEC": "SEC", "ACC": "ACC", "Big Ten": "Big Ten", "Big 12": "Big 12"}


def load_polls(season):
    """({week: {school: (rank, points)}}, {week: voters}) for regular-season AP polls."""
    data = json.loads((RAW / "polls" / f"rankings_{season}_regular.json").read_text())
    polls, voters = {}, {}
    for week in data:
        for poll in week["polls"]:
            if poll["poll"] == "AP Top 25":
                polls[week["week"]] = {r["school"]: (r["rank"], r["points"])
                                       for r in poll["ranks"]}
                voters[week["week"]] = sum(r["firstPlaceVotes"] or 0 for r in poll["ranks"])
    weeks = sorted(polls)
    if weeks != list(range(1, len(weeks) + 1)):
        sys.exit(f"{season}: AP poll weeks not contiguous from 1: {weeks}")
    return polls, voters


def load_games(season):
    s = pd.read_parquet(RAW / "schedules" / f"cfb_schedules_{season}.parquet")
    s = s[(s.season_type == "regular") & s.completed
          & ((s.home_division == "fbs") | (s.away_division == "fbs"))].copy()
    # A game counts toward week w only if it kicked off by Tuesday 12:00 ET after
    # the week's busiest game day; later games come after the poll (DEVIATIONS.md).
    kick_et = pd.to_datetime(s.start_date, utc=True).dt.tz_convert("America/New_York")
    busiest = kick_et.dt.normalize().groupby(s.week).agg(lambda d: d.mode().iloc[0])
    cutoff = s.week.map(busiest) + pd.Timedelta(days=3, hours=12)
    late = kick_et > cutoff
    for _, g in s[late].iterrows():
        print(f"  dropped {season} week {g.week}: {g.away_team} at {g.home_team} ({g.start_date})")
    return s[~late]


def poll_points(poll, treatment, divisor=1):
    """Points lookup with the unranked value for this poll and treatment."""
    unranked = 0.0 if treatment == "zero" else 0.5 * min(p for _, p in poll.values())
    return {t: p / divisor for t, (_, p) in poll.items()}, unranked / divisor


def team_games(games):
    """Long format: one row per team per game, from that team's side."""
    cols = ["game_id", "week", "start_date", "neutral_site"]
    home = games[cols + ["home_team", "home_division", "home_conference", "home_points",
                         "away_team", "away_points", "home_pregame_elo", "home_postgame_elo"]].copy()
    home.columns = cols + ["team", "division", "conference", "pf", "opp", "pa", "elo", "elo_post"]
    home["venue"] = np.where(home.neutral_site, "neutral", "home")
    away = games[cols + ["away_team", "away_division", "away_conference", "away_points",
                         "home_team", "home_points", "away_pregame_elo", "away_postgame_elo"]].copy()
    away.columns = cols + ["team", "division", "conference", "pf", "opp", "pa", "elo", "elo_post"]
    away["venue"] = np.where(away.neutral_site, "neutral", "away")
    return pd.concat([home, away], ignore_index=True)


def build_season(season):
    polls, voters = load_polls(season)
    games = load_games(season)
    tg = team_games(games)
    fbs = tg[tg.division == "fbs"]
    teams = sorted(fbs.team.unique())
    conference = fbs.groupby("team").conference.agg(lambda c: c.mode().iloc[0])

    for week, poll in polls.items():
        missing = set(poll) - set(teams)
        if missing:
            sys.exit(f"{season} week {week}: AP teams not in FBS schedule: {sorted(missing)}")

    rows = []
    for w in range(1, max(polls)):
        prior, nxt = polls[w], polls[w + 1]
        wk = tg[tg.week == w]
        lost = set(wk.team[wk.pf < wk.pa])
        rank_of = {t: r for t, (r, _) in prior.items()}
        pts = {(unit, tr): (poll_points(prior, tr, div[0]), poll_points(nxt, tr, div[1]))
               for tr in TREATMENTS
               for unit, div in (("points", (1, 1)), ("ppv", (voters[w], voters[w + 1])))}
        to_date = tg[tg.week <= w]
        for team in teams:
            g = wk[wk.team == team]
            td = to_date[to_date.team == team]
            rank = rank_of.get(team, 26)
            row = {
                "season": season, "week": w, "team": team,
                "conference": conference[team],
                "conf_group": CONF_GROUPS.get(conference[team], "Other"),
                "prior_rank": rank_of.get(team),
                "next_rank": nxt[team][0] if team in nxt else None,
                "games": len(g),
                "wins": int((g.pf > g.pa).sum()),
                "losses": int((g.pf < g.pa).sum()),
                "bye": int(len(g) == 0),
                "points_for": float(g.pf.sum()),
                "points_against": float(g.pa.sum()),
                "margin": float((g.pf - g.pa).sum()),
                "home": int((g.venue == "home").sum()),
                "away": int((g.venue == "away").sum()),
                "neutral": int((g.venue == "neutral").sum()),
                "losses_above": sum(1 for t, r in rank_of.items() if r < rank and t in lost),
                "opponents": ";".join(g.opp),
                "wins_to_date": int((td.pf > td.pa).sum()),
                "losses_to_date": int((td.pf < td.pa).sum()),
                "margin_to_date": float((td.pf - td.pa).mean()) if len(td) else 0.0,
                "voters_prior": voters[w],
                "voters_next": voters[w + 1],
                "elo": float(g.elo.mean()) if len(g) and g.elo.notna().all() else None,
                "elo_post": (float(td.sort_values("start_date").elo_post.iloc[-1])
                             if len(td) and pd.notna(td.sort_values("start_date").elo_post.iloc[-1])
                             else None),
                "last_game_date": g.start_date.max() if len(g) else None,
            }
            for (unit, tr), ((p_prior, u_prior), (p_next, u_next)) in pts.items():
                before = p_prior.get(team, u_prior)
                after = p_next.get(team, u_next)
                row[f"prior_{unit}_{tr}"] = before
                row[f"next_{unit}_{tr}"] = after
                row[f"target_{unit}_{tr}"] = after - before
                row[f"opp_{unit}_{tr}"] = float(sum(p_prior.get(o, u_prior) for o in g.opp))
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    table = pd.concat([build_season(s) for s in SEASONS], ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False)
    counts = table.groupby("season").size()
    print(f"Wrote {len(table)} team-weeks to {OUT.relative_to(ROOT)}")
    print(counts.to_string())


if __name__ == "__main__":
    main()
