"""Bias tests (DEVIATIONS.md, 2026-10-23: rating-aware model, voter-bias test,
schedule-inflation test; Elo kept as a comparison).

  1. Rewards and punishments: residuals of the name-blind rated model, each
     2014-2025 season predicted by a model fit on the other seasons, by conference
     for ranked teams after a win, after a loss, and over all weeks.
  2. Schedule inflation: each team's schedule ranked by opponents' poll points and
     by opponents' season-only rating; inflation = rating rank - poll rank.
  3. Head start: Elo rank (carries last season) versus season-only rating rank,
     by conference, polls 6+.

95% intervals: 1,000 resamples of whole team-seasons (seed 0).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from train import features, make_models, target

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
RATINGS = ROOT / "data" / "processed" / "season_ratings.csv"
OUT = ROOT / "results" / "bias_tests.json"
SEASONS = [s for s in range(2014, 2026) if s != 2020]
CONFS = ["SEC", "ACC", "Big Ten", "Big 12", "Other"]
FCS = "FCS (pooled)"
N_BOOT = 1000


def group_means(df, value, rng):
    """Mean of `value` per conference + SEC-ACC, CIs from resampling team-seasons."""
    per = df.groupby(["season", "team", "conf_group"])[value].agg(["sum", "count"]).reset_index()
    out, boots = {}, {}
    for c in CONFS:
        p = per[per.conf_group == c]
        s, n = p["sum"].to_numpy(), p["count"].to_numpy()
        if len(p) == 0:
            continue
        idx = rng.integers(0, len(p), size=(N_BOOT, len(p)))
        boots[c] = s[idx].sum(1) / n[idx].sum(1)
        out[c] = {"mean": float(s.sum() / n.sum()), "n": int(n.sum()),
                  "team_seasons": int(len(p)),
                  "ci": [float(x) for x in np.percentile(boots[c], [2.5, 97.5])]}
    d = boots["SEC"] - boots["ACC"]
    out["sec_minus_acc"] = float(out["SEC"]["mean"] - out["ACC"]["mean"])
    out["sec_minus_acc_ci"] = [float(x) for x in np.percentile(d, [2.5, 97.5])]
    return out


def rewards_and_punishments(tw, treatment, rng):
    d = tw[tw.season.isin(SEASONS)].copy()
    X, y = d[features(treatment, "rated")], d[target(treatment, "rated")]
    d["pred"] = np.nan
    for season in SEASONS:
        test = d.season == season
        model = make_models()["gbt"]
        model.fit(X[~test], y[~test])
        d.loc[test, "pred"] = model.predict(X[test])
    d["residual"] = y - d.pred
    ranked = d[d.prior_rank.notna()]
    win = (ranked.wins > 0) & (ranked.losses == 0)
    loss = ranked.losses > 0
    return {
        "ranked_all_weeks": group_means(ranked, "residual", rng),
        "ranked_after_win": group_means(ranked[win], "residual", rng),
        "ranked_after_loss": group_means(ranked[loss], "residual", rng),
        "unit": "AP points per voter (one rank spot is about 0.8)",
        "note": "Positive after a win = rewarded more than results explain; "
                "positive after a loss = punished less.",
    }


def schedule_inflation(tw, ratings, seasons, rng):
    poll = tw.set_index(["season", "week", "team"]).prior_ppv_zero
    last = ratings.groupby("season").week.transform("max") == ratings.week
    final = ratings[last].set_index(["season", "team"]).combined
    rows = []
    for (season, team), g in tw[tw.season.isin(seasons) & (tw.games > 0)].groupby(["season", "team"]):
        poll_vals, rating_vals = [], []
        for week, opps in zip(g.week, g.opponents):
            for o in opps.split(";"):
                poll_vals.append(poll.get((season, week, o), 0.0))
                rating_vals.append(final.get((season, o), final[(season, FCS)]))
        rows.append({"season": season, "team": team, "conf_group": g.conf_group.iloc[0],
                     "poll_sos": np.mean(poll_vals), "rating_sos": np.mean(rating_vals)})
    s = pd.DataFrame(rows)
    s["poll_rank"] = s.groupby("season").poll_sos.rank(ascending=False, method="min")
    s["rating_rank"] = s.groupby("season").rating_sos.rank(ascending=False, method="min")
    s["inflation"] = s.rating_rank - s.poll_rank
    out = group_means(s, "inflation", rng)
    for c in CONFS:
        sc = s[s.conf_group == c]
        out[c]["mean_poll_sos_rank"] = float(sc.poll_rank.mean())
        out[c]["mean_rating_sos_rank"] = float(sc.rating_rank.mean())
    out["note"] = ("Schedule-strength rank among FBS teams (1 = toughest). inflation = rating "
                   "rank - poll rank; positive = the poll makes the schedule look tougher "
                   "than opponents' results do.")
    return out, s


def head_start(tw, ratings, rng):
    d = tw[tw.season.isin(SEASONS) & (tw.week >= 5)].sort_values(["season", "team", "week"]).copy()
    d["elo_after"] = tw.sort_values(["season", "team", "week"]).groupby(
        ["season", "team"]).elo_post.ffill().reindex(d.index)
    d = d.merge(ratings[["season", "week", "team", "strength_rank"]],
                on=["season", "week", "team"]).dropna(subset=["elo_after"])
    d["elo_rank"] = d.groupby(["season", "week"]).elo_after.rank(ascending=False, method="min")
    e, r = d.elo_rank.clip(upper=26), d.strength_rank.clip(upper=26)
    d = d[(e <= 25) | (r <= 25)].copy()
    d["head_start"] = r[d.index] - e[d.index]
    out = group_means(d, "head_start", rng)
    out["note"] = ("Season-only rating rank - Elo rank (capped at 26), polls 6+; positive = "
                   "Elo rates the team higher than this season's results alone.")
    return out


def main():
    tw = pd.read_csv(TABLE)
    ratings = pd.read_csv(RATINGS)
    report = {"rewards_and_punishments": {}}
    for tr in ("zero", "floor"):
        report["rewards_and_punishments"][tr] = rewards_and_punishments(
            tw, tr, np.random.default_rng(0))
    infl, table = schedule_inflation(tw, ratings, SEASONS, np.random.default_rng(0))
    report["schedule_inflation_2014_2025"] = infl
    report["schedule_inflation_2026_to_date"], t26 = schedule_inflation(
        tw, ratings, [2026], np.random.default_rng(0))
    report["head_start_elo_vs_season_rating"] = head_start(tw, ratings, np.random.default_rng(0))
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    t26.sort_values("poll_rank").to_csv(ROOT / "results" / "schedule_strength_2026.csv", index=False)

    def show(title, block, fmt="{:+.2f}"):
        print(f"\n{title}")
        for c in CONFS:
            x = block[c]
            print(f"  {c:8} {fmt.format(x['mean'])}  CI {fmt.format(x['ci'][0])} to "
                  f"{fmt.format(x['ci'][1])}  (n={x['n']})")
        print(f"  SEC-ACC {fmt.format(block['sec_minus_acc'])}  CI "
              f"{fmt.format(block['sec_minus_acc_ci'][0])} to {fmt.format(block['sec_minus_acc_ci'][1])}")

    rp = report["rewards_and_punishments"]["zero"]
    show("1a. Ranked teams after a WIN: residual (ppv)", rp["ranked_after_win"])
    show("1b. Ranked teams after a LOSS: residual (ppv)", rp["ranked_after_loss"])
    show("1c. Ranked teams, all weeks: residual (ppv)", rp["ranked_all_weeks"])
    show("2. Schedule inflation 2014-2025 (rank spots of 130ish)", infl, "{:+.1f}")
    for c in CONFS:
        print(f"     {c:8} avg schedule rank by poll {infl[c]['mean_poll_sos_rank']:.0f}, "
              f"by rating {infl[c]['mean_rating_sos_rank']:.0f}")
    i26 = report["schedule_inflation_2026_to_date"]
    print("   2026 to date: " + ", ".join(
        f"{c} {i26[c]['mean']:+.1f} (poll {i26[c]['mean_poll_sos_rank']:.0f} / rating "
        f"{i26[c]['mean_rating_sos_rank']:.0f})" for c in CONFS))
    show("3. Head start: Elo vs this-season rating (rank spots)", report["head_start_elo_vs_season_rating"])


if __name__ == "__main__":
    main()
