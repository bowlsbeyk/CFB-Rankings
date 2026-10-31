"""T6: were SEC teams ranked higher in the early polls than their full season justified?
(DEVIATIONS.md, 2026-10-31.)

Compares the AP top 25 in polls 1-5 (preseason and the first four in-season polls) with
the end-of-regular-season top 25 by ranking-independent measures built only from that
season's results (strength of record, Colley wins-and-losses, performance), 2014-2025.
Excess = AP slots - final-measure slots, averaged over polls 1-5, by group. Same
statistics, groups, tie rules and reading as T5. Also redoes T1 with strength of record:
did preseason-ranked SEC teams fall further short of their preseason rank than is typical?

Writes results/t6_early.json.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from season_rating import colley
from sor_test import (BAND, FCS, GROUPS, HIST, POWER_OTHERS, PRIMARY, SIGMA, bench_value,
                      boot_seasons, group_of, offsets_from_t4, performance_fast, schedule_arrays,
                      season_games, shares, sor_probs, tstats, variants)

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
OUT = ROOT / "results" / "t6_early.json"
EARLY_POLLS = (1, 2, 3, 4, 5)


def final_measures(season, tw, offsets):
    """End-of-regular-season SOR (all variants), Colley and performance for FBS teams."""
    games, _ = season_games(season)
    teams = sorted((set(games.home) | set(games.away)) - {FCS}) + [FCS]
    n = len(teams)
    fbs = teams[:-1]
    s_tw = tw[tw.season == season]
    conf = s_tw.drop_duplicates("team").set_index("team").conference
    grp = pd.Series({t: group_of(conf.get(t, "FCS"), t, season) for t in fbs})
    last_w = int(s_tw.week.max())
    played = games[games.week <= last_w]
    opp, ven, mask, wins, hi, ai = schedule_arrays(played, teams, list(range(n - 1)))
    home = np.where(played.neutral_site.to_numpy(), 0.0, 1.0)
    r, h = performance_fast(hi, ai, home, played.margin.to_numpy(), n)
    d = pd.DataFrame({"team": fbs, "group": grp[fbs].to_numpy(), "wins": wins,
                      "performance": r[:-1], "colley": colley(played, teams)[fbs].to_numpy()})
    for name, bench, mult, off in variants():
        rr = r.copy()
        if off:
            rr[:-1] = rr[:-1] + grp[fbs].map(offsets[off]).fillna(0.0).to_numpy()
        d[f"sor_{name}"] = sor_probs(opp, ven, wins, mask, rr, h, bench_value(rr[:-1], bench), SIGMA * mult)
        if off:
            d[f"perf_{off}"] = rr[:-1]
    return d.set_index("team")


def early_excess(season, tw, final, key, ascending, use="slots", polls=EARLY_POLLS):
    """Mean over the given AP polls of AP minus final-measure slots (or rank points), by group."""
    k = final[key] if ascending else -final[key]
    m_slot, m_pts = shares(k)
    grp = final.group
    s_tw = tw[tw.season == season].set_index(["week", "team"]).prior_rank  # week w row = AP poll w
    acc = {}
    for p in polls:
        ap = pd.Series([s_tw.get((p, t), np.nan) for t in final.index], index=final.index)
        a_slot, a_pts = shares(ap)
        for G in GROUPS:
            sel = grp == G
            if sel.any():
                a = a_slot[sel].sum() if use == "slots" else a_pts[sel].sum()
                m = m_slot[sel].sum() if use == "slots" else m_pts[sel].sum()
                acc.setdefault(G, []).append(float(a - m))
    return {G: float(np.mean(v)) for G, v in acc.items()}


def quantities(per):
    e, dp, da = [], [], []
    for s in HIST:
        x = per[s]
        e.append(x["SEC"])
        dp.append(x["SEC"] - np.mean([x[G] for G in POWER_OTHERS if G in x]))
        da.append(x["SEC"] - x["ACC"])
    return {"E_SEC": e, "D_PWR": dp, "D_ACC": da}


def label_part1(e, dpwr):
    over = e["ci95_t"][0] > 0 and e["seasons_positive"] >= 9
    consistent = e["ci90_t"][0] >= -BAND and e["ci90_t"][1] <= BAND
    under = e["ci95_t"][1] < 0 and e["seasons_positive"] <= 2
    specific = dpwr["ci95_t"][0] > 0 and dpwr["seasons_positive"] >= 9
    if over:
        lab = "RANKED HIGHER EARLY THAN THE SEASON JUSTIFIED, " + (
            "SEC-SPECIFIC" if specific else "SHARED WITH THE OTHER POWER CONFERENCES, NOT SEC-SPECIFIC")
        return lab + (" (by less than half a slot per poll)" if consistent else "")
    if consistent:
        return "EARLY RANKINGS CONSISTENT WITH HOW THE SEASON TURNED OUT"
    if under:
        return "RANKED LOWER EARLY THAN THE SEASON JUSTIFIED"
    return "INCONCLUSIVE"


def label_part2(d):
    if d["ci95_t"][0] > 0 and d["seasons_positive"] >= 9:
        return "SEC early excess HIGHER than ACC"
    if d["ci95_t"][1] < 0 and d["seasons_positive"] <= 2:
        return "SEC early excess LOWER than ACC"
    return "INCONCLUSIVE"


def main():
    tw = pd.read_csv(TABLE)
    offsets = offsets_from_t4()
    finals = {s: final_measures(s, tw, offsets) for s in HIST}
    prim = f"sor_{PRIMARY[0]}|x{PRIMARY[1]}"
    report = {"early_polls": list(EARLY_POLLS), "primary_variant": prim}

    per = {s: early_excess(s, tw, finals[s], prim, True) for s in HIST}
    q = quantities(per)
    st = {k: tstats(v) for k, v in q.items()}
    for k in st:
        st[k]["bootstrap_seasons_ci95"] = boot_seasons(q[k])
    report["primary"] = st
    report["by_group"] = {G: float(np.mean([per[s][G] for s in HIST if G in per[s]])) for G in GROUPS}
    report["label_part1"] = label_part1(st["E_SEC"], st["D_PWR"])
    report["label_part2"] = label_part2(st["D_ACC"])

    gate = {}
    for name, *_ in variants():
        p = {s: early_excess(s, tw, finals[s], f"sor_{name}", True) for s in HIST}
        gate[f"SOR {name}"] = {k: float(np.mean(v)) for k, v in quantities(p).items()}
    p = {s: early_excess(s, tw, finals[s], prim, True, use="pts") for s in HIST}
    gate["rank points"] = {k: float(np.mean(v)) for k, v in quantities(p).items()}
    for key, nm in (("colley", "final Colley top 25"), ("performance", "final performance top 25")):
        p = {s: early_excess(s, tw, finals[s], key, False) for s in HIST}
        gate[nm] = {k: float(np.mean(v)) for k, v in quantities(p).items()}
    robust = {}
    for k in ("E_SEC", "D_PWR", "D_ACC"):
        m0 = st[k]["mean"]
        vals = [g[k] for g in gate.values()]
        robust[k] = {"same_sign_everywhere": bool(all(np.sign(v) == np.sign(m0) for v in vals)),
                     "within_band_everywhere": bool(all(abs(v) <= BAND for v in vals)),
                     "min": float(min(vals)), "max": float(max(vals))}
    report["robustness_gate"] = {"by_check": gate, "summary": robust}

    # Preseason poll alone (descriptive).
    pp = {s: early_excess(s, tw, finals[s], prim, True, polls=(1,)) for s in HIST}
    report["preseason_poll_only"] = {k: tstats(v) for k, v in quantities(pp).items()}

    # T1 redone with strength of record: adjusted shortfall of preseason-ranked teams.
    rows = []
    for s in HIST:
        f = finals[s]
        sor_rank = f[prim].rank(method="average").clip(upper=26)
        pre = tw[(tw.season == s) & (tw.week == 1)].set_index("team").prior_rank.dropna()
        for t, r0 in pre.items():
            if t in f.index:
                rows.append({"season": s, "team": t, "group": f.group[t], "pre_rank": r0,
                             "final_sor_rank": float(sor_rank[t])})
    pr = pd.DataFrame(rows)
    pr["shortfall"] = pr.final_sor_rank - pr.pre_rank
    slope, intercept = np.polyfit(pr.pre_rank, pr.shortfall, 1)
    pr["adjusted"] = pr.shortfall - (intercept + slope * pr.pre_rank)
    by = pr.groupby(["season", "group"]).adjusted.mean().unstack()
    a = {"A_SEC": [], "D_PWR": [], "D_ACC": []}
    for s in HIST:
        row = by.loc[s]
        a["A_SEC"].append(row["SEC"])
        a["D_PWR"].append(row["SEC"] - np.nanmean([row.get(G, np.nan) for G in POWER_OTHERS]))
        a["D_ACC"].append(row["SEC"] - row["ACC"] if pd.notna(row.get("ACC")) else np.nan)
    a = {k: [x for x in v if pd.notna(x)] for k, v in a.items()}
    report["preseason_shortfall_vs_SOR"] = {
        "fit": {"intercept": float(intercept), "slope": float(slope)},
        "by_group_mean_adjusted": pr.groupby("group").adjusted.mean().round(3).to_dict(),
        "by_group_share_outside_final_SOR_top25": pr.assign(out=pr.final_sor_rank > 25)
        .groupby("group").out.mean().round(3).to_dict(),
        "by_group_n": pr.groupby("group").size().to_dict(),
        **{k: tstats(v) for k, v in a.items()},
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("PART 1:", report["label_part1"])
    print("PART 2:", report["label_part2"])
    for k in ("E_SEC", "D_PWR", "D_ACC"):
        x = st[k]
        print(f"  {k}: {x['mean']:+.2f} (95% t {x['ci95_t'][0]:+.2f}, {x['ci95_t'][1]:+.2f}) "
              f"positive {x['seasons_positive']}/11, sign-flip p {x['sign_flip_p']:.3f}")
    print("robust:", json.dumps(robust))
    ps = report["preseason_shortfall_vs_SOR"]
    print("preseason shortfall vs SOR A_SEC:", round(ps["A_SEC"]["mean"], 2), ps["A_SEC"]["ci95_t"],
          "D_PWR:", round(ps["D_PWR"]["mean"], 2), ps["D_PWR"]["ci95_t"])


if __name__ == "__main__":
    main()
