"""Exploratory team bias finder (not pre-registered; see DEVIATIONS.md).

For each team, compares how its AP points actually moved with what the model
predicted, using out-of-season predictions on the 2014-2023 training seasons
(each season predicted by a model that never saw it). The model has no team or
conference input, so a team that is consistently over- or under-predicted is
treated differently by voters than its results alone would suggest.

Residual = actual change - predicted change, in AP poll points.
  Negative after a loss while ranked: the team fell further than predicted.
  Positive after a win while ranked: the team rose more than predicted.

95% intervals come from resampling a team's seasons with replacement.

Usage:
  python src/team_bias.py                       # leaderboard + conference summary
  python src/team_bias.py --team Miami          # one team, season by season
  python src/team_bias.py --model linear --treatment floor
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OOF = ROOT / "data" / "processed" / "oof_predictions.csv"
RESULTS = ROOT / "results"

SITUATIONS = {
    "ranked_all": lambda d: d.prior_rank.notna(),
    "ranked_win": lambda d: d.prior_rank.notna() & (d.wins > 0) & (d.losses == 0),
    "ranked_loss": lambda d: d.prior_rank.notna() & (d.losses > 0),
}
MIN_WEEKS = 20
N_BOOT = 2000


def load(model, treatment):
    d = pd.read_csv(OOF)
    d = d[d.treatment == treatment].copy()
    d["residual"] = d.target - d[f"pred_{model}"]
    return d


def boot_ci(per_season_sum, per_season_n, rng):
    """95% CI of the mean residual, resampling whole seasons."""
    k = len(per_season_sum)
    if k < 2:
        return np.nan, np.nan
    idx = rng.integers(0, k, size=(N_BOOT, k))
    sums, ns = per_season_sum[idx].sum(1), per_season_n[idx].sum(1)
    means = sums[ns > 0] / ns[ns > 0]
    return tuple(np.percentile(means, [2.5, 97.5]))


def summarize(d, group_col, rng):
    rows = []
    for key, g in d.groupby(group_col):
        row = {group_col: key, "seasons_ranked": g[g.prior_rank.notna()].season.nunique()}
        for name, select in SITUATIONS.items():
            s = g[select(g)]
            per = s.groupby("season").residual.agg(["sum", "count"])
            row[f"{name}_weeks"] = len(s)
            row[f"{name}_mean"] = s.residual.mean() if len(s) else np.nan
            lo, hi = boot_ci(per["sum"].to_numpy(), per["count"].to_numpy(), rng)
            row[f"{name}_lo"], row[f"{name}_hi"] = lo, hi
        rows.append(row)
    return pd.DataFrame(rows)


def rank_gap(d):
    """Median AP points between adjacent ranks, to read residuals as rank spots."""
    r = d[d.prior_rank.notna()].sort_values(["season", "week", "prior_rank"])
    gaps = r.groupby(["season", "week"]).prior_points.diff().abs()
    return float(gaps.median())


def fmt(mean, lo, hi):
    if np.isnan(mean):
        return "      n/a"
    flag = "*" if (lo > 0 or hi < 0) else " "
    return f"{mean:+7.1f}{flag} [{lo:+.0f}, {hi:+.0f}]"


def print_board(table, label_col, title, gap):
    print(f"\n{title}")
    print(f"(AP points; one rank spot is about {gap:.0f} points; * = 95% interval excludes 0)")
    print(f"{'':24}{'weeks':>6}  {'ranked, any':>22}  {'after a win':>22}  {'after a loss':>22}")
    for _, r in table.iterrows():
        print(f"{str(r[label_col])[:24]:24}{int(r.ranked_all_weeks):6}  "
              f"{fmt(r.ranked_all_mean, r.ranked_all_lo, r.ranked_all_hi):>22}  "
              f"{fmt(r.ranked_win_mean, r.ranked_win_lo, r.ranked_win_hi):>22}  "
              f"{fmt(r.ranked_loss_mean, r.ranked_loss_lo, r.ranked_loss_hi):>22}")


def team_detail(d, team, gap):
    t = d[(d.team == team) & d.prior_rank.notna()]
    if t.empty:
        raise SystemExit(f"No ranked weeks for {team!r} in training seasons")
    print(f"\n{team}: ranked weeks in 2014-2023 training seasons "
          f"(one rank spot is about {gap:.0f} points)")
    print(f"{'season':>6} {'week':>4} {'rank':>4} {'result':>6} {'opponents':24} "
          f"{'actual':>7} {'predicted':>9} {'residual':>8}")
    for _, r in t.sort_values(["season", "week"]).iterrows():
        res = "bye" if r.bye else ("L" if r.losses else "W")
        print(f"{r.season:6} {r.week:4} {int(r.prior_rank):4} {res:>6} "
              f"{str(r.opponents if isinstance(r.opponents, str) else '')[:24]:24} "
              f"{r.target:7.0f} {r.prediction:9.0f} {r.residual:+8.0f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", default="gbt", choices=["gbt", "linear"])
    ap.add_argument("--treatment", default="zero", choices=["zero", "floor"])
    ap.add_argument("--team")
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    d = load(args.model, args.treatment)
    gap = rank_gap(d)
    if args.team:
        tw = pd.read_csv(ROOT / "data" / "processed" / "team_weeks.csv",
                         usecols=["season", "week", "team", "opponents"])
        d = d.merge(tw, on=["season", "week", "team"], how="left")
        d["prediction"] = d[f"pred_{args.model}"]
        team_detail(d, args.team, gap)
        return

    rng = np.random.default_rng(0)
    teams = summarize(d, "team", rng)
    confs = summarize(d, "conf_group", rng)
    tag = f"{args.model}_{args.treatment}"
    RESULTS.mkdir(exist_ok=True)
    teams.round(2).to_csv(RESULTS / f"team_bias_{tag}.csv", index=False)
    confs.round(2).to_csv(RESULTS / f"conference_bias_{tag}.csv", index=False)

    print(f"Exploratory, training seasons 2014-2023 only. Model {args.model}, "
          f"unranked rule {args.treatment}.")
    print("Read with care: about 70 teams x 3 situations are tested, so some * appear by "
          "chance;\nteams that sit near #1 cannot rise much, so they can look under-rewarded.")
    print_board(confs.sort_values("ranked_all_mean"), "conf_group",
                "By conference group", gap)
    eligible = teams[teams.ranked_all_weeks >= MIN_WEEKS]
    board = eligible.sort_values("ranked_loss_mean")
    print_board(board.head(args.top), "team",
                f"Fell furthest beyond prediction after losses (>= {MIN_WEEKS} ranked weeks)", gap)
    print_board(board.dropna(subset=["ranked_loss_mean"]).tail(args.top).iloc[::-1], "team",
                "Most protected after losses", gap)
    print_board(eligible.sort_values("ranked_all_mean", ascending=False).head(args.top), "team",
                "Most over-rewarded while ranked, all weeks", gap)
    print_board(eligible.sort_values("ranked_all_mean").head(args.top), "team",
                "Most under-rewarded while ranked, all weeks", gap)


if __name__ == "__main__":
    main()
