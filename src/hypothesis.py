"""Hypothesis test on real 2014-2025 data (no 2020). Definitions: DEVIATIONS.md
(2026-10-23, hypothesis test definitions).

  1. Conference effect: SEC-minus-ACC coefficient in the linear poll-movement model.
  2. Poll versus Elo: gap between Elo rank and AP rank, by conference, plus the
     "Elo top 25 but AP unranked" / "AP ranked but outside Elo top 25" table.
  3. Preseason carry-over: how much preseason standing persists in later polls at
     equal record, margin and Elo, overall and for SEC vs ACC.

95% intervals: 1,000 bootstrap resamples of whole team-seasons (seed 0),
implemented as integer weights per team-season.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from train import features, target

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
OUT = ROOT / "results" / "hypothesis.json"
RATINGS = ROOT / "data" / "processed" / "season_ratings.csv"
SEASONS = [s for s in range(2014, 2026) if s != 2020]
CONFS = ["SEC", "ACC", "Big Ten", "Big 12"]
N_BOOT = 1000


def boot_weights(groups, rng):
    """(N_BOOT, n_rows) integer weights from resampling whole groups."""
    codes, uniq = pd.factorize(groups)
    k = len(uniq)
    draws = rng.integers(0, k, size=(N_BOOT, k))
    counts = np.stack([np.bincount(d, minlength=k) for d in draws])
    return counts[:, codes]


def wls(X, y, w=None):
    X1 = np.column_stack([np.ones(len(X)), X])
    if w is not None:
        sw = np.sqrt(w)
        X1, y = X1 * sw[:, None], y * sw
    return np.linalg.lstsq(X1, y, rcond=None)[0][1:]


def ci(values):
    lo, hi = np.percentile(values, [2.5, 97.5])
    return [float(lo), float(hi)]


def with_elo(tw):
    tw = tw.sort_values(["season", "team", "week"]).copy()
    tw["elo_after"] = tw.groupby(["season", "team"]).elo_post.ffill()
    return tw


def conference_effect(tw, treatment, spec, rng):
    d = tw.dropna(subset=features(treatment, spec)).copy()
    dummies = pd.get_dummies(d.conf_group)[CONFS].astype(float)
    cols = features(treatment, spec)
    X = np.column_stack([d[cols].to_numpy(float), dummies.to_numpy()])
    y = d[target(treatment, spec)].to_numpy(float)
    i_sec, i_acc = len(cols), len(cols) + 1
    beta = wls(X, y)
    W = boot_weights(d.season.astype(str) + "|" + d.team, rng)
    diffs = []
    for w in W:
        b = wls(X, y, w.astype(float))
        diffs.append(b[i_sec] - b[i_acc])
    return {"coef": {c: float(beta[len(cols) + j]) for j, c in enumerate(CONFS)},
            "sec_minus_acc": float(beta[i_sec] - beta[i_acc]),
            "sec_minus_acc_ci": ci(diffs),
            "unit": "AP points per voter" if spec == "revised" else "AP points",
            "reference": "Other (Pac-12, Group of 5, independents)"}


def poll_vs_elo(tw, rng, col="elo_after", min_week=1):
    """Poll versus a strength measure (Elo, or the season-only rating)."""
    d = tw[tw.week >= min_week].dropna(subset=[col]).copy()
    d["elo_rank"] = d.groupby(["season", "week"])[col].rank(ascending=False, method="min")
    d["ap_rank"] = d.next_rank.fillna(26).clip(upper=26)
    d["elo_rank_c"] = d.elo_rank.clip(upper=26)
    u = d[(d.ap_rank <= 25) | (d.elo_rank_c <= 25)].copy()
    u["gap"] = u.elo_rank_c - u.ap_rank
    W = boot_weights(u.season.astype(str) + "|" + u.team, rng)
    out = {}
    means = {}
    for c in CONFS + ["Other"]:
        m = (u.conf_group == c).to_numpy()
        g = u.gap.to_numpy()[m]
        bw = W[:, m]
        means[c] = (bw * g).sum(1) / np.maximum(bw.sum(1), 1)
        out[c] = {"team_weeks": int(m.sum()), "mean_gap": float(g.mean()), "ci": ci(means[c]),
                  "elo_top25_ap_unranked": int(((u.conf_group == c) & (u.elo_rank_c <= 25)
                                                & (u.ap_rank > 25)).sum()),
                  "ap_ranked_outside_elo_top25": int(((u.conf_group == c) & (u.ap_rank <= 25)
                                                      & (u.elo_rank_c > 25)).sum())}
    out["sec_minus_acc"] = float(out["SEC"]["mean_gap"] - out["ACC"]["mean_gap"])
    out["sec_minus_acc_ci"] = ci(means["SEC"] - means["ACC"])
    out["note"] = (f"gap = strength rank ({col}) - AP rank, capped at 26; positive = poll "
                   "rates team above the strength measure")
    snubs = u[(u.elo_rank_c <= 15) & (u.ap_rank > 25)].sort_values("elo_rank")
    out["biggest_snubs"] = [
        {"season": int(r.season), "poll_week": int(r.week) + 1, "team": r.team,
         "conference": r.conf_group, "elo_rank": int(r.elo_rank),
         "record": f"{int(r.wins_to_date)}-{int(r.losses_to_date)}"}
        for _, r in snubs.head(15).iterrows()]
    return out


def preseason_carryover(tw, treatment, rng, col="elo_after", min_week=4):
    pre = tw[tw.week == 1].set_index(["season", "team"])[f"prior_ppv_{treatment}"]
    d = tw[tw.week >= min_week].dropna(subset=[col]).copy()
    d["pre"] = d.set_index(["season", "team"]).index.map(pre)
    controls = ["wins_to_date", "losses_to_date", "margin_to_date", col, "week"]
    y = d[f"next_ppv_{treatment}"].to_numpy(float)
    groups = d.season.astype(str) + "|" + d.team
    W = boot_weights(groups, rng)

    X = d[["pre"] + controls].to_numpy(float)
    b = wls(X, y)
    boots = [wls(X, y, w.astype(float))[0] for w in W]

    sec = (d.conf_group == "SEC").to_numpy(float)
    acc = (d.conf_group == "ACC").to_numpy(float)
    X2 = np.column_stack([X, d.pre * sec, d.pre * acc, sec, acc])
    b2 = wls(X2, y)
    i_s, i_a = X.shape[1], X.shape[1] + 1
    diffs = []
    for w in W:
        bb = wls(X2, y, w.astype(float))
        diffs.append(bb[i_s] - bb[i_a])
    return {
        "preseason_coef": float(b[0]), "preseason_coef_ci": ci(boots),
        "controls": controls,
        "extra_carryover_sec": float(b2[i_s]), "extra_carryover_acc": float(b2[i_a]),
        "sec_minus_acc": float(b2[i_s] - b2[i_a]), "sec_minus_acc_ci": ci(diffs),
        "team_weeks": int(len(d)),
        "note": ("Coefficient = points per voter later in the season per point per voter "
                 "in the preseason poll, at equal record, margin, Elo and week (polls 5+). "
                 "Elo carries part of the prior season, so this likely understates carry-over."),
    }


def main():
    tw = with_elo(pd.read_csv(TABLE))
    tw = tw[tw.season.isin(SEASONS)]
    report = {}
    for tr in ("zero", "floor"):
        rng = np.random.default_rng(0)
        report[tr] = {
            "conference_effect": {s: conference_effect(tw, tr, s, rng)
                                  for s in ("revised", "registered")},
            "preseason_carryover": preseason_carryover(tw, tr, rng),
        }
    report["poll_vs_elo"] = poll_vs_elo(tw, np.random.default_rng(0))

    # Primary yardstick since 2026-10-23: the season-only rating (DEVIATIONS.md),
    # polls 6+ (rating after at least five weeks of games).
    sr = pd.read_csv(RATINGS)[["season", "week", "team", "combined"]]
    tws = tw.merge(sr.rename(columns={"combined": "season_rating"}),
                   on=["season", "week", "team"], how="left")
    report["season_rating"] = {
        "poll_vs_rating": poll_vs_elo(tws, np.random.default_rng(0), "season_rating", 5),
        "preseason_carryover": {
            tr: preseason_carryover(tws, tr, np.random.default_rng(0), "season_rating", 5)
            for tr in ("zero", "floor")},
    }
    report["note"] = "Real data 2014-2025 (no 2020); primary unranked rule: zero."
    OUT.write_text(json.dumps(report, indent=2) + "\n")

    for tr in ("zero", "floor"):
        ce = report[tr]["conference_effect"]["revised"]
        pc = report[tr]["preseason_carryover"]
        print(f"[{tr}] 1. SEC-ACC movement, same game: {ce['sec_minus_acc']:+.3f} ppv "
              f"CI {ce['sec_minus_acc_ci'][0]:+.3f} to {ce['sec_minus_acc_ci'][1]:+.3f}")
        print(f"[{tr}] 3. preseason carry-over {pc['preseason_coef']:.3f} "
              f"CI {pc['preseason_coef_ci'][0]:.3f}-{pc['preseason_coef_ci'][1]:.3f}; "
              f"SEC-ACC extra {pc['sec_minus_acc']:+.3f} CI {pc['sec_minus_acc_ci'][0]:+.3f} "
              f"to {pc['sec_minus_acc_ci'][1]:+.3f}")
    pe = report["poll_vs_elo"]
    print("2. poll vs Elo gap (positive = poll above Elo):")
    for c in CONFS + ["Other"]:
        x = pe[c]
        print(f"   {c:8} {x['mean_gap']:+.2f} CI {x['ci'][0]:+.2f} to {x['ci'][1]:+.2f}  "
              f"n={x['team_weeks']}  Elo-top25/AP-unranked {x['elo_top25_ap_unranked']}  "
              f"AP-ranked/outside-Elo-top25 {x['ap_ranked_outside_elo_top25']}")
    print(f"   SEC-ACC {pe['sec_minus_acc']:+.2f} CI {pe['sec_minus_acc_ci'][0]:+.2f} "
          f"to {pe['sec_minus_acc_ci'][1]:+.2f}")
    sr = report["season_rating"]
    print("SEASON-ONLY RATING (primary yardstick), polls 6+:")
    for c in CONFS + ["Other"]:
        x = sr["poll_vs_rating"][c]
        print(f"   {c:8} {x['mean_gap']:+.2f} CI {x['ci'][0]:+.2f} to {x['ci'][1]:+.2f}  "
              f"n={x['team_weeks']}  rated-top25/AP-unranked {x['elo_top25_ap_unranked']}  "
              f"AP-ranked/outside-rated-top25 {x['ap_ranked_outside_elo_top25']}")
    pv = sr["poll_vs_rating"]
    print(f"   SEC-ACC {pv['sec_minus_acc']:+.2f} CI {pv['sec_minus_acc_ci'][0]:+.2f} "
          f"to {pv['sec_minus_acc_ci'][1]:+.2f}")
    for tr in ("zero", "floor"):
        pc = sr["preseason_carryover"][tr]
        print(f"   [{tr}] carry-over {pc['preseason_coef']:.3f} CI {pc['preseason_coef_ci'][0]:.3f}-"
              f"{pc['preseason_coef_ci'][1]:.3f}; SEC-ACC extra {pc['sec_minus_acc']:+.3f} "
              f"CI {pc['sec_minus_acc_ci'][0]:+.3f} to {pc['sec_minus_acc_ci'][1]:+.3f}")


if __name__ == "__main__":
    main()
