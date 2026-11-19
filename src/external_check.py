"""T9: our yardsticks against ESPN's strength of record and SP+ (DEVIATIONS.md, 2026-11-19).

Descriptive validity check, not a bias test. Our end-of-regular-season strength-of-record rank is
compared with ESPN's strength-of-record rank, and our end-of-regular-season margin (performance)
rank with the SP+ rank: per-season Spearman agreement, and a conference lean (our rank minus the
external rank, among the external top 40; positive = ours ranks the group's teams worse).
External historical values are final (after bowls); ours stop at the regular season.

Writes results/t9_external.json and results/t9_2026_board.csv (AP top 25 with all four ranks).
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sor_test import HIST, tstats  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "advanced"
OUT = ROOT / "results" / "t9_external.json"
BOARD = ROOT / "results" / "t9_2026_board.csv"
OTHERS = ["ACC", "Big Ten", "Big 12", "Pac-12"]
TOP = 40


def external(season):
    """{team: (espn_sor_rank, sp_rank)} or None if the files are missing."""
    try:
        fpi = json.loads((RAW / f"fpi_{season}.json").read_text())
        sp = json.loads((RAW / f"sp_{season}.json").read_text())
    except FileNotFoundError:
        return None
    e = {x["team"]: (x.get("resumeRanks") or {}).get("strengthOfRecord") for x in fpi}
    s = {x["team"]: x.get("ranking") for x in sp if x["team"] != "nationalAverages"}
    return pd.DataFrame({"espn_sor": pd.Series(e, dtype=float), "sp_rank": pd.Series(s, dtype=float)})


def final_ours(weekly, season):
    d = weekly[weekly.season == season]
    d = d[d.week == d.week.max()].set_index("team")
    return d[["group", "sor_rank", "perf_rank"]]


def lean(df, ours, ext):
    d = df.dropna(subset=[ours, ext])
    d = d.assign(ours_r=d[ours].rank(method="average"), ext_r=d[ext].rank(method="average"))
    top = d[d.ext_r <= TOP]
    g = (top.ours_r - top.ext_r).groupby(top.group).mean()
    return {"rho": float(spearmanr(d[ours], d[ext]).statistic),
            "lean": {k: float(v) for k, v in g.items()},
            "sec_minus_others": float(g.get("SEC", np.nan) - np.mean([g[x] for x in OTHERS if x in g])),
            "sec_minus_acc": float(g.get("SEC", np.nan) - g.get("ACC", np.nan))}


def reading(x):
    if x["ci90_t"][0] >= -2 and x["ci90_t"][1] <= 2:
        return "TREATS THE SEC AS THE EXTERNAL MEASURE DOES (within 2 ranks)"
    if x["ci95_t"][0] > 0 and x["seasons_positive"] >= 9:
        return "OURS IS HARSHER ON THE SEC"
    if x["ci95_t"][1] < 0 and x["seasons_positive"] <= 2:
        return "OURS IS KINDER TO THE SEC"
    return "INCONCLUSIVE"


def main():
    weekly = pd.read_csv(ROOT / "results" / "sor_weekly.csv")
    report = {"note": "descriptive validity check; external historical values are final (after bowls), "
                      "ours end with the regular season", "top_n_for_lean": TOP}
    for label, ours, ext in (("our_SOR_vs_ESPN_SOR", "sor_rank", "espn_sor"), ("our_margin_vs_SP+", "perf_rank", "sp_rank")):
        per = {}
        for s in HIST:
            df = final_ours(weekly, s).join(external(s), how="inner")
            per[s] = lean(df, ours, ext)
        rho = [per[s]["rho"] for s in HIST]
        smo = tstats([per[s]["sec_minus_others"] for s in HIST])
        sma = tstats([per[s]["sec_minus_acc"] for s in HIST])
        groups = sorted({g for s in HIST for g in per[s]["lean"]})
        report[label] = {
            "spearman_mean": float(np.mean(rho)), "spearman_min": float(np.min(rho)),
            "lean_by_group_mean": {g: float(np.mean([per[s]["lean"][g] for s in HIST if g in per[s]["lean"]]))
                                   for g in groups},
            "SEC_minus_other_power_lean": smo, "reading": reading(smo),
            "SEC_minus_ACC_lean": sma, "reading_vs_ACC": reading(sma),
            "per_season": {str(s): per[s] for s in HIST}}

    ext26 = external(2026)
    if ext26 is not None and not ext26.dropna(how="all").empty:
        sor26 = pd.read_csv(ROOT / "results" / "sor_2026.csv").set_index("team")
        b = sor26[sor26.ap_rank.notna()][["group", "record", "ap_rank", "sor_rank", "perf_rank"]].join(ext26)
        b = b.sort_values("ap_rank")
        b.to_csv(BOARD)
        report["2026_snapshot_2026-11-19"] = {
            "spearman_SOR_vs_ESPN_all_FBS": float(spearmanr(*sor26.join(ext26, how="inner")[["sor_rank", "espn_sor"]].dropna().T.values).statistic),
            "spearman_margin_vs_SP+_all_FBS": float(spearmanr(*sor26.join(ext26, how="inner")[["perf_rank", "sp_rank"]].dropna().T.values).statistic),
            "board_file": str(BOARD.relative_to(ROOT)),
            "timing": "ours after week 11; ESPN and SP+ as published on 2026-11-19 (may include week 12)"}
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    for k in ("our_SOR_vs_ESPN_SOR", "our_margin_vs_SP+"):
        r = report[k]
        x, y = r["SEC_minus_other_power_lean"], r["SEC_minus_ACC_lean"]
        print(f"{k}: rho {r['spearman_mean']:.3f} (min {r['spearman_min']:.3f}); SEC-others lean {x['mean']:+.2f} "
              f"({x['ci95_t'][0]:+.2f} to {x['ci95_t'][1]:+.2f}, {x['seasons_positive']}/11) -> {r['reading']}; "
              f"SEC-ACC {y['mean']:+.2f} ({y['ci95_t'][0]:+.2f} to {y['ci95_t'][1]:+.2f}) -> {r['reading_vs_ACC']}")
        print("   lean by group:", {g: round(v, 2) for g, v in r["lean_by_group_mean"].items()})
    if "2026_snapshot_2026-11-19" in report:
        print("2026:", {k: v for k, v in report["2026_snapshot_2026-11-19"].items() if k.startswith("spearman")})


if __name__ == "__main__":
    main()
