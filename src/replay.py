"""Season replay: run real games through a model, feeding it its own simulated poll.

Used for the end-of-season pass test and the 2026 counterfactual. Mechanics are
fixed in DEVIATIONS.md (2026-10-23, replay details).

Run directly, this is a training-data check: each 2014-2023 season is replayed by
a model fit without that season, and the simulated final poll is compared with
the real one. It also measures stickiness: how far the replay keeps
preseason-ranked teams above their real final rank. It never loads the
2024-2025 holdout.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from train import SPECS, TRAIN_SEASONS, UNIT, features, make_models, target

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "results"


def unranked_value(points, treatment):
    if treatment == "zero":
        return 0.0
    return 0.5 * np.sort(points)[-25]


def _apply_cutoff(pts, treatment):
    rank = pts.rank(ascending=False, method="min")
    out = pts.copy()
    out[rank > 25] = unranked_value(pts.values, treatment)
    return out


def replay(season_rows, model, treatment, start_points, spec="revised"):
    """Replay one season.

    season_rows: team_weeks rows for one season (real games).
    start_points: {team: preseason value in the spec's unit}; others are unranked.
    Returns {week: DataFrame(points, shadow, sim_rank)} for polls 2..N, where
    week w is the poll after schedule week w-1 (same numbering as CFBD).
    """
    u = UNIT[spec]
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
        unranked = unranked_value(pts.values, treatment)
        opp_points = g.opponents.fillna("").map(
            lambda s: float(sum(pts.get(o, unranked) for o in s.split(";") if o)))
        X = g.assign(**{f"prior_{u}_{treatment}": pts,
                        f"opp_{u}_{treatment}": opp_points,
                        "losses_above": losses_above})[features(treatment, spec)]
        pts = _apply_cutoff((pts + model.predict(X)).clip(lower=0), treatment)
        in_top = pts.rank(ascending=False, method="min") <= 25
        shadow[in_top] = pts[in_top]
        polls[w + 1] = pd.DataFrame({
            "points": pts, "shadow": shadow,
            "sim_rank": shadow.rank(ascending=False, method="average")})
    return polls


def real_poll(season, week=None, season_type="regular"):
    data = json.loads((RAW / "polls" / f"rankings_{season}_{season_type}.json").read_text())
    polls = {w["week"]: {r["school"]: r for r in p["ranks"]}
             for w in data for p in w["polls"] if p["poll"] == "AP Top 25"}
    if not polls:
        return None
    return polls[week if week is not None else max(polls)]


def start_values(season, spec):
    """Real preseason values in the spec's unit."""
    poll = real_poll(season, 1)
    voters = sum(r["firstPlaceVotes"] or 0 for r in poll.values())
    div = voters if spec == "revised" else 1
    return {t: r["points"] / div for t, r in poll.items()}


def compare(sim_rank, real):
    """Spearman and overlap over the real top 25 (DEVIATIONS.md definition)."""
    teams = [t for t in real if t in sim_rank.index]
    real_rank = np.array([real[t]["rank"] for t in teams])
    sim = sim_rank[teams].to_numpy()
    sim_top = set(sim_rank.nsmallest(25).index)
    return {
        "spearman": float(spearmanr(real_rank, sim)[0]),
        "overlap": len(sim_top & set(real)),
        "mean_abs_rank_error": float(np.mean(np.abs(real_rank - sim))),
        "within_3": float(np.mean(np.abs(real_rank - sim) <= 3)),
    }


def stickiness(sim_rank, real, preseason):
    """Inertia measures for one season (ranks capped at 26 = unranked)."""
    real_cap = {t: real[t]["rank"] if t in real else 26 for t in sim_rank.index}
    sim_cap = sim_rank.clip(upper=26)
    pre = [t for t in preseason if t in sim_rank.index]
    sim_top = set(sim_rank.nsmallest(25).index)
    return {
        "spots_kept_above_real": float(np.mean([real_cap[t] - sim_cap[t] for t in pre])),
        "preseason_ranked_still_ranked_real": len(set(pre) & set(real)),
        "preseason_ranked_still_ranked_sim": len(set(pre) & sim_top),
        "climbers_real": len(set(real) - set(preseason)),
        "climbers_sim": len(sim_top - set(preseason)),
        "climbers_caught": len((set(real) - set(preseason)) & sim_top),
    }


def preseason_ranks(season_rows, start):
    s = pd.Series(0.0, index=sorted(season_rows.team.unique()))
    for t, p in start.items():
        s[t] = p
    return s.rank(ascending=False, method="average")


def training_check(treatment, model_name, spec):
    tw = pd.read_csv(TABLE)
    train = tw[tw.season.isin(TRAIN_SEASONS)]
    out, curves = {}, []
    for season in TRAIN_SEASONS:
        rows = train[train.season == season]
        fit_on = train[train.season != season]
        model = make_models()[model_name]
        model.fit(fit_on[features(treatment, spec)], fit_on[target(treatment, spec)])
        start = start_values(season, spec)
        polls = replay(rows, model, treatment, start, spec)
        final_week = max(polls)
        final_real = real_poll(season, final_week)
        res = {
            "final_regular": compare(polls[final_week].sim_rank, final_real),
            "preseason_unchanged_vs_final_regular":
                compare(preseason_ranks(rows, start), final_real),
            "stickiness": stickiness(polls[final_week].sim_rank, final_real, start),
        }
        post = real_poll(season, season_type="postseason")
        if post:
            res["post_bowl_final"] = compare(polls[final_week].sim_rank, post)
        out[season] = res
        for w, p in polls.items():
            curves.append({"season": season, "poll_week": w,
                           **compare(p.sim_rank, real_poll(season, w))})
    return out, pd.DataFrame(curves)


def summarize(out):
    sp = [v["final_regular"]["spearman"] for v in out.values()]
    st = pd.DataFrame([v["stickiness"] for v in out.values()])
    return {
        "spearman_mean": float(np.mean(sp)),
        "spearman_min": float(np.min(sp)),
        "seasons_passing_0.7": int(sum(x >= 0.7 for x in sp)),
        "seasons": len(sp),
        "overlap_mean": float(np.mean([v["final_regular"]["overlap"] for v in out.values()])),
        "preseason_unchanged_spearman_mean": float(np.mean(
            [v["preseason_unchanged_vs_final_regular"]["spearman"] for v in out.values()])),
        "stickiness_spots_mean": float(st.spots_kept_above_real.mean()),
        "climbers_real": int(st.climbers_real.sum()),
        "climbers_sim": int(st.climbers_sim.sum()),
        "climbers_caught": int(st.climbers_caught.sum()),
        "preseason_still_ranked_real": int(st.preseason_ranked_still_ranked_real.sum()),
        "preseason_still_ranked_sim": int(st.preseason_ranked_still_ranked_sim.sum()),
    }


def main():
    report = {}
    for spec in SPECS:
        for tr in ("zero", "floor"):
            for model_name in ("gbt", "linear"):
                out, curve = training_check(tr, model_name, spec)
                key = f"{spec}_{model_name}_{tr}"
                s = summarize(out)
                report[key] = {"summary": s, "by_season": {str(k): v for k, v in out.items()}}
                curve.to_csv(RESULTS / f"replay_training_curve_{key}.csv", index=False)
                print(f"[{key}] Spearman mean {s['spearman_mean']:.2f}, min {s['spearman_min']:.2f}, "
                      f"{s['seasons_passing_0.7']}/{s['seasons']} >= 0.7, overlap {s['overlap_mean']:.1f}"
                      f" | climbers {s['climbers_sim']} sim vs {s['climbers_real']} real "
                      f"({s['climbers_caught']} caught) | preseason still ranked "
                      f"{s['preseason_still_ranked_sim']} vs {s['preseason_still_ranked_real']}"
                      f" | stickiness {s['stickiness_spots_mean']:+.2f} spots")
    report["note"] = ("Training seasons only; each season replayed by a model fit "
                      "without it. Pass threshold for the holdout: Spearman >= 0.7. "
                      "Stickiness = mean rank spots the replay keeps preseason-ranked "
                      "teams above their real final rank (26 = unranked).")
    (RESULTS / "replay_training.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
