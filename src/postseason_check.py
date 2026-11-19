"""Postseason records by conference, 2014-2025 (no 2020) (DEVIATIONS.md, 2026-11-19; descriptive).

FBS-vs-FBS postseason games from data/raw/postseason/. Conference groups as in T5, by each
season's membership. Writes results/postseason_by_conference.json and results/postseason_games.csv.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sor_test import HIST, group_of  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "postseason"
RES = ROOT / "results"
POWER = ["SEC", "Big Ten", "Big 12", "ACC", "Pac-12"]


def rec(x):
    return {"games": int(len(x)), "wins": int(x.won.sum()), "losses": int((~x.won).sum()),
            "win_share": round(float(x.won.mean()), 3) if len(x) else None}


def main():
    rows = []
    for s in HIST:
        for g in json.loads((RAW / f"games_{s}_postseason.json").read_text()):
            if not g.get("completed") or g.get("homeClassification") != "fbs" or g.get("awayClassification") != "fbs":
                continue
            if g.get("homePoints") is None or g.get("awayPoints") is None or g["homePoints"] == g["awayPoints"]:
                continue
            po = g.get("playoff") or {}
            cfp = po.get("competition") == "cfp"
            for t, c, o, oc, pf, pa in ((g["homeTeam"], g["homeConference"], g["awayTeam"], g["awayConference"], g["homePoints"], g["awayPoints"]),
                                        (g["awayTeam"], g["awayConference"], g["homeTeam"], g["homeConference"], g["awayPoints"], g["homePoints"])):
                rows.append({"season": s, "date": g["startDate"][:10], "team": t, "group": group_of(c, t, s),
                             "opponent": o, "opp_group": group_of(oc, o, s), "points_for": pf, "points_against": pa,
                             "won": pf > pa, "cfp": cfp, "cfp_round": po.get("round") if cfp else None})
    d = pd.DataFrame(rows)
    d.to_csv(RES / "postseason_games.csv", index=False)

    out = {"note": "descriptive; FBS-vs-FBS postseason games; conference by each season's membership; no rating uses these"}
    eras = {"2014-2019": d[d.season <= 2019], "2021-2025": d[d.season >= 2021], "all": d}
    for name, e in eras.items():
        out[name] = {}
        for G in POWER + ["Notre Dame", "Other"]:
            x = e[e.group == G]
            if not len(x):
                continue
            vp = x[x.opp_group.isin(POWER) & (x.opp_group != G)]
            out[name][G] = {"all_postseason": rec(x), "vs_other_power_conferences": rec(vp),
                            "playoff": rec(x[x.cfp]), "non_playoff_bowls": rec(x[~x.cfp])}
    champs = {}
    for s in HIST:
        f = d[(d.season == s) & d.cfp & d.won].sort_values("date")
        if len(f):
            champs[str(s)] = {"champion": f.iloc[-1].team, "group": f.iloc[-1].group}
    out["national_champions"] = champs
    out["SEC_by_season"] = {str(s): {**rec(d[(d.season == s) & (d.group == "SEC")]),
                                     "playoff": rec(d[(d.season == s) & (d.group == "SEC") & d.cfp])} for s in HIST}
    (RES / "postseason_by_conference.json").write_text(json.dumps(out, indent=2) + "\n")

    print("champions:", {s: f"{c['champion']} ({c['group']})" for s, c in champs.items()})
    for name in ("2014-2019", "2021-2025"):
        print(f"\n{name}:")
        for G, v in out[name].items():
            a, p, b = v["all_postseason"], v["vs_other_power_conferences"], v["playoff"]
            print(f"  {G:10s} all {a['wins']:3d}-{a['losses']:<3d} ({a['win_share']:.0%})  vs power {p['wins']:3d}-{p['losses']:<3d}"
                  f" ({(p['win_share'] or 0):.0%})  playoff {b['wins']}-{b['losses']}")
    print("\nSEC by season:", {s: f"{v['wins']}-{v['losses']} (CFP {v['playoff']['wins']}-{v['playoff']['losses']})" for s, v in out["SEC_by_season"].items()})


if __name__ == "__main__":
    main()
