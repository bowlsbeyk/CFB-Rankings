"""Season replay: run real games through a model, feeding it its own simulated poll.

Used for the end-of-season pass test and the 2026 counterfactual. Mechanics are
fixed in DEVIATIONS.md (2026-10-23, replay details).

Run directly, this is a training-data check: each 2014-2023 season is replayed by
a model fit without that season, and the simulated final poll is compared with
the real one. It never loads the 2024-2025 holdout.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from train import TRAIN_SEASONS, features, make_models

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "results"


def unranked_value(points, treatment):
    if treatment == "zero":
        return 0.0
    return 0.5 * np.sort(points)[-25]


def replay(season_rows, model, treatment, start_points):
    """Replay one season.

    season_rows: team_weeks rows for one season (real games).
    start_points: {team: preseason points}; teams not listed are unranked.
    Returns {week: DataFrame(team, points, shadow, sim_rank)} for polls 2..N,
    where week w is the poll after schedule week w-1 (same numbering as CFBD).
    """
    teams = sorted(season_rows.team.unique())
    pts = pd.Series(0.0, index=teams)
    for t, p in start_points.items():
        pts[t] = p
    pts = _apply_cutoff(pts, treatment)
    shadow = pts.copy()
    polls = {}
    for w, g in season_rows.groupby("week"):
        g = g.set_index("team").loc[teams]
        rank = pts.rank(ascending=False, method="min")
        ranked = rank <= 25
        lost = g.losses > 0
        losses_above = pd.Series(
            [int(((rank < rank[t]) & ranked & lost).sum()) if ranked[t]
             else int((ranked & lost).sum()) for t in teams], index=teams)
        opp_points = g.opponents.fillna("").map(
            lambda s: float(sum(pts.get(o, unranked_value(pts.values, treatment))
                                for o in s.split(";") if o)))
        X = g.assign(**{f"prior_points_{treatment}": pts,
                        f"opp_points_{treatment}": opp_points,
                        "losses_above": losses_above})[features(treatment)]
        pts = _apply_cutoff((pts + model.predict(X)).clip(lower=0), treatment)
        in_top = pts.rank(ascending=False, method="min") <= 25
        shadow[in_top] = pts[in_top]
        polls[w + 1] = pd.DataFrame({
            "points": pts, "shadow": shadow,
            "sim_rank": shadow.rank(ascending=False, method="average")})
    return polls


def _apply_cutoff(pts, treatment):
    rank = pts.rank(ascending=False, method="min")
    out = pts.copy()
    out[rank > 25] = unranked_value(pts.values, treatment)
    return out


def real_poll(season, week=None, season_type="regular"):
    data = json.loads((RAW / "polls" / f"rankings_{season}_{season_type}.json").read_text())
    polls = {w["week"]: {r["school"]: r for r in p["ranks"]}
             for w in data for p in w["polls"] if p["poll"] == "AP Top 25"}
    if not polls:
        return None
    return polls[week if week is not None else max(polls)]


def compare(sim_rank, real):
    """Spearman and overlap over the real top 25 (DEVIATIONS.md definition)."""
    teams = [t for t in real if t in sim_rank.index]
    real_rank = [real[t]["rank"] for t in teams]
    sim = sim_rank[teams].to_numpy()
    sim_top = set(sim_rank.nsmallest(25).index)
    return {
        "spearman": float(spearmanr(real_rank, sim)[0]),
        "overlap": len(sim_top & set(real)),
        "mean_abs_rank_error": float(np.mean(np.abs(np.array(real_rank) - sim))),
        "within_3": float(np.mean(np.abs(np.array(real_rank) - sim) <= 3)),
    }


def preseason_ranks(season_rows, start):
    teams = sorted(season_rows.team.unique())
    s = pd.Series(0.0, index=teams)
    for t, p in start.items():
        s[t] = p
    return s.rank(ascending=False, method="average")


def training_check(treatment, model_name):
    tw = pd.read_csv(TABLE)
    train = tw[tw.season.isin(TRAIN_SEASONS)]
    out, curves = {}, []
    for season in TRAIN_SEASONS:
        rows = train[train.season == season]
        fit_on = train[train.season != season]
        model = make_models()[model_name]
        model.fit(fit_on[features(treatment)], fit_on[f"target_{treatment}"])
        start = {t: float(r["points"]) for t, r in real_poll(season, 1).items()}
        polls = replay(rows, model, treatment, start)
        final_week = max(polls)
        pre = preseason_ranks(rows, start)
        res = {
            "final_regular": compare(polls[final_week].sim_rank, real_poll(season, final_week)),
            "preseason_unchanged_vs_final_regular": compare(pre, real_poll(season, final_week)),
        }
        post = real_poll(season, season_type="postseason")
        if post:
            res["post_bowl_final"] = compare(polls[final_week].sim_rank, post)
        out[season] = res
        for w, p in polls.items():
            c = compare(p.sim_rank, real_poll(season, w))
            curves.append({"season": season, "poll_week": w, **c})
    return out, pd.DataFrame(curves)


def main():
    report = {}
    for tr in ("zero", "floor"):
        for model_name in ("gbt", "linear"):
            out, curve = training_check(tr, model_name)
            key = f"{model_name}_{tr}"
            report[key] = {str(k): v for k, v in out.items()}
            curve.to_csv(RESULTS / f"replay_training_curve_{key}.csv", index=False)
            sp = [v["final_regular"]["spearman"] for v in out.values()]
            base = [v["preseason_unchanged_vs_final_regular"]["spearman"] for v in out.values()]
            ov = [v["final_regular"]["overlap"] for v in out.values()]
            print(f"[{key}] final-regular Spearman by season: "
                  + ", ".join(f"{s}:{x:.2f}" for s, x in zip(out, sp))
                  + f" | min {min(sp):.2f}, mean {np.mean(sp):.2f}; overlap mean {np.mean(ov):.1f}/25"
                  + f" | preseason-unchanged mean {np.mean(base):.2f}")
    report["note"] = ("Training seasons only; each season replayed by a model fit "
                      "without it. Pass threshold for the holdout: Spearman >= 0.7.")
    (RESULTS / "replay_training.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
