"""Checks on data/processed/team_weeks.csv. Run build_features.py first."""

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"


@pytest.fixture(scope="module")
def tw():
    return pd.read_csv(TABLE)


def ap_polls(season):
    data = json.loads((ROOT / "data" / "raw" / "polls" / f"rankings_{season}_regular.json").read_text())
    return {w["week"]: {r["school"]: r for r in p["ranks"]}
            for w in data for p in w["polls"] if p["poll"] == "AP Top 25"}


def schedule(season):
    s = pd.read_parquet(ROOT / "data" / "raw" / "schedules" / f"cfb_schedules_{season}.parquet")
    return s[(s.season_type == "regular") & s.completed]


def test_no_2020_and_all_other_seasons_present(tw):
    assert sorted(tw.season.unique()) == [s for s in range(2014, 2027) if s != 2020]


def test_one_row_per_team_week(tw):
    assert not tw.duplicated(["season", "week", "team"]).any()


def test_row_counts_are_teams_times_transitions(tw):
    for season, g in tw.groupby("season"):
        n_transitions = max(ap_polls(season)) - 1
        assert g.week.nunique() == n_transitions
        assert len(g) == g.team.nunique() * n_transitions


def test_every_ranked_team_has_a_row(tw):
    for season, g in tw.groupby("season"):
        polls = ap_polls(season)
        for week, wg in g.groupby("week"):
            assert set(polls[week]) == set(wg.team[wg.prior_rank.notna()])
            assert set(polls[week + 1]) == set(wg.team[wg.next_rank.notna()])


def test_prior_points_come_from_the_earlier_poll(tw):
    """Each row's prior points equal the previous row's next points for that team."""
    for tr in ("zero", "floor"):
        t = tw.sort_values(["season", "team", "week"])
        prev_next = t.groupby(["season", "team"])[f"next_points_{tr}"].shift()
        has_prev = prev_next.notna()
        assert (t.loc[has_prev, f"prior_points_{tr}"] == prev_next[has_prev]).all()


def test_games_finish_before_the_next_week_starts(tw):
    """Features use only games played before the following week's kickoffs,
    so they precede the poll each row predicts."""
    for season, g in tw.groupby("season"):
        first_kick = schedule(season).groupby("week").start_date.min()
        played = g.dropna(subset=["last_game_date"])
        nxt = played.week.map(lambda w: first_kick.get(w + 1))
        has_next = nxt.notna()
        assert (played.last_game_date[has_next] < nxt[has_next]).all(), season


def test_targets_are_point_differences(tw):
    for tr in ("zero", "floor"):
        diff = tw[f"next_points_{tr}"] - tw[f"prior_points_{tr}"]
        assert (diff == tw[f"target_{tr}"]).all()


def test_unranked_values(tw):
    unranked = tw[tw.prior_rank.isna()]
    assert (unranked.prior_points_zero == 0).all()
    ranked_min = tw[tw.prior_rank.notna()].groupby(["season", "week"]).prior_points_zero.min()
    floor = unranked.groupby(["season", "week"]).prior_points_floor.agg(["min", "max"])
    assert (floor["min"] == floor["max"]).all()
    assert (floor["min"] == 0.5 * ranked_min.loc[floor.index]).all()


def test_game_encoding(tw):
    assert ((tw.wins + tw.losses) == tw.games).all()
    assert ((tw.home + tw.away + tw.neutral) == tw.games).all()
    assert (tw.bye == (tw.games == 0)).all()
    assert (tw.margin == tw.points_for - tw.points_against).all()
