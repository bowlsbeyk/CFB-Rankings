"""Era split: 2014-2019 against 2021-2025, the seasons since NIL rules took effect
(DEVIATIONS.md, 2026-11-19; post hoc, descriptive). Writes results/era_check.json.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as tdist

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sor_test import HIST, group_of, shares  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RAW = ROOT / "data" / "raw"
OUT = RES / "era_check.json"
EARLY = [s for s in HIST if s <= 2019]
RECENT = [s for s in HIST if s >= 2021]
OTHERS = ["ACC", "Big Ten", "Big 12", "Pac-12"]


def compare(per_season):
    """per_season: {season: value}. Era means and Welch interval for recent minus early."""
    a = np.array([per_season[s] for s in EARLY if s in per_season and not pd.isna(per_season[s])], float)
    b = np.array([per_season[s] for s in RECENT if s in per_season and not pd.isna(per_season[s])], float)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = np.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    d = b.mean() - a.mean()
    q = tdist.ppf(0.975, df)
    return {"per_season": {str(s): round(float(v), 3) for s, v in per_season.items() if not pd.isna(v)},
            "early_2014_2019": round(float(a.mean()), 3), "recent_2021_2025": round(float(b.mean()), 3),
            "recent_minus_early": round(float(d), 3), "ci95_welch": [round(float(d - q * se), 3), round(float(d + q * se), 3)]}


def main():
    rep = {"note": "post hoc, descriptive; 6 and 5 seasons, little power; DEVIATIONS.md 2026-11-19"}

    # On the field: SOR top-25 counts.
    w = pd.read_csv(RES / "sor_weekly.csv")
    w = w[w.season.isin(HIST)]
    sec, diff = {}, {G: {} for G in OTHERS}
    for s, ds in w.groupby("season"):
        c = {G: [] for G in ["SEC"] + OTHERS}
        for _, d in ds.groupby("week"):
            sl, _ = shares(d.set_index("team").sor_rank)
            g = d.set_index("team").group
            for G in c:
                if (g == G).any():
                    c[G].append(sl[g == G].sum())
        sec[s] = np.mean(c["SEC"])
        for G in OTHERS:
            if c[G]:
                diff[G][s] = np.mean(c["SEC"]) - np.mean(c[G])
    rep["field_SEC_strength_of_record_top25_per_poll"] = compare(sec)
    rep["field_SEC_minus_conference_SOR_top25"] = {G: compare(v) for G, v in diff.items() if len(v) >= 8}

    g = pd.read_csv(RES / "t4_referee_games.csv")
    vp = g[(g.conference == "SEC") & (g.opp_power)]
    rep["field_SEC_vs_power_outsiders_win_share"] = compare(vp.groupby("season").won.mean().to_dict())
    rep["field_SEC_vs_power_outsiders_residual"] = compare(vp.groupby("season").residual.mean().to_dict())
    rep["field_SEC_vs_power_outsiders_games"] = {"early": int(vp[vp.season <= 2019].shape[0]),
                                                 "recent": int(vp[vp.season >= 2021].shape[0])}

    champs = {}
    for s in HIST:
        sc = pd.read_parquet(RAW / "schedules" / f"cfb_schedules_{s}.parquet")
        f = sc[(sc.season_type == "postseason") & sc.notes.fillna("").str.contains("National Championship", case=False)]
        if len(f):
            x = f.iloc[0]
            win, conf = ((x.home_team, x.home_conference) if x.home_points > x.away_points
                         else (x.away_team, x.away_conference))
            champs[str(s)] = {"champion": win, "conference": conf}
    rep["national_champions"] = champs

    # In the polls.
    tw = pd.read_csv(ROOT / "data" / "processed" / "team_weeks.csv", usecols=["season", "week", "team", "conf_group", "next_rank"])
    tw = tw[tw.season.isin(HIST) & (tw.week >= 5)]
    ap = {s: d[d.conf_group == "SEC"].groupby("week").next_rank.apply(lambda r: (r <= 25).sum()).mean()
          for s, d in tw.groupby("season")}
    rep["polls_SEC_AP_top25_per_poll"] = compare(ap)
    pre = {}
    for s in HIST:
        data = json.loads((RAW / "polls" / f"rankings_{s}_regular.json").read_text())
        for wk in data:
            for p in wk["polls"]:
                if p["poll"] == "AP Top 25" and wk["week"] == 1:
                    pre[s] = sum(1 for r in p["ranks"] if group_of(r.get("conference"), r["school"], s) == "SEC")
    rep["polls_SEC_preseason_AP_top25"] = compare(pre)
    t5 = json.loads((RES / "t5_sor.json").read_text())
    rep["polls_T5_AP_minus_SOR_SEC"] = compare(dict(zip(HIST, t5["primary"]["E_SEC"]["per_season"])))
    t6 = json.loads((RES / "t6_early.json").read_text())
    rep["polls_T6_early_polls_minus_final_SOR_SEC"] = compare(dict(zip(HIST, t6["primary"]["E_SEC"]["per_season"])))
    pairs = pd.read_csv(RES / "t8_pairs.csv")
    rep["polls_T8_same_record_premium_SEC"] = compare(pairs.groupby("season")["diff"].mean().to_dict())

    # T8 allowing for how the season ended, per season (the verification check's regression).
    from committee_common import frames
    from verification_checks import pairs as vpairs
    allw = frames()
    out = {}
    for G in ("SEC", "ACC"):
        p = vpairs(allw, G)
        per = {}
        for s in HIST:
            q = p[p.season == s]
            if len(q) >= 6:
                X = np.column_stack([np.ones(len(q)), q.sor_gap, q.perf_gap, q.final_sor_gap])
                per[s] = float(np.linalg.lstsq(X, q["diff"].to_numpy(), rcond=None)[0][0])
        out[G] = compare(per)
        out[G + "_unadjusted"] = compare(p.groupby("season")["diff"].mean().to_dict())
    rep["polls_T8_allowing_for_how_season_ended"] = out

    OUT.write_text(json.dumps(rep, indent=2) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    for k, v in rep.items():
        if isinstance(v, dict) and "recent_minus_early" in v:
            print(f"{k:48s} early {v['early_2014_2019']:+.2f}  recent {v['recent_2021_2025']:+.2f}  "
                  f"diff {v['recent_minus_early']:+.2f} ({v['ci95_welch'][0]:+.2f} to {v['ci95_welch'][1]:+.2f})")
    for G, v in rep["field_SEC_minus_conference_SOR_top25"].items():
        print(f"  SEC minus {G:8s} SOR top25: early {v['early_2014_2019']:+.2f} recent {v['recent_2021_2025']:+.2f} diff {v['recent_minus_early']:+.2f} ({v['ci95_welch'][0]:+.2f} to {v['ci95_welch'][1]:+.2f})")
    for G, v in rep["polls_T8_allowing_for_how_season_ended"].items():
        print(f"  T8 {G:15s}: early {v['early_2014_2019']:+.2f} recent {v['recent_2021_2025']:+.2f} diff {v['recent_minus_early']:+.2f} ({v['ci95_welch'][0]:+.2f} to {v['ci95_welch'][1]:+.2f})")
    print("games vs power outsiders:", rep["field_SEC_vs_power_outsiders_games"])
    print("champions:", {s: f"{c['champion']} ({c['conference']})" for s, c in champs.items()})


if __name__ == "__main__":
    main()
