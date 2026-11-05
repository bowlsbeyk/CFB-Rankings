"""T7: does the playoff committee rank the SEC above its results? (DEVIATIONS.md, 2026-11-05.)

T5's test with the Playoff Committee Rankings in place of the AP poll: per committee ranking,
each group's committee top-25 slots minus its strength-of-record top-25 slots (results through
the previous schedule week); mean over the season's rankings; E_SEC, D_PWR and D_ACC across
2014-2025 (no 2020), with T5's labels and 14-check robustness gate. Secondary: committee minus
AP in the same week. Descriptive: the playoff bubble (places 6-16).

Writes results/t7_committee.json.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from committee_common import committee_frames, committee_ranks, frames  # noqa: E402
from sor_test import (GROUPS, HIST, PRIMARY, gate_summary, gate_verdict, label_part1,  # noqa: E402
                      label_part2, quantities, season_excess, shares, tstats, variants)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "t7_committee.json"


def bubble_excess(frame, key_col):
    """Per ranking: slots in committee places 6-16 minus slots in places 6-16 of key_col."""
    acc = {}
    for _, d in frame.groupby("week"):
        d = d.set_index("team")
        c = shares(d.ap_rank, 16)[0] - shares(d.ap_rank, 5)[0]
        m = shares(d[key_col], 16)[0] - shares(d[key_col], 5)[0]
        for G in GROUPS:
            sel = d.group == G
            if sel.any():
                acc.setdefault(G, []).append(float(c[sel].sum() - m[sel].sum()))
    return {G: float(np.mean(v)) for G, v in acc.items()}


def main():
    allw = frames()
    cfp = committee_ranks()
    cf, unmatched = committee_frames(allw, cfp)
    prim = f"sor_{PRIMARY[0]}|x{PRIMARY[1]}"
    by = {s: cf[cf.season == s] for s in HIST}
    report = {"rankings_per_season": {s: int(by[s].cfp_week.nunique()) for s in HIST},
              "committee_schools_not_matched": unmatched}

    per = {s: season_excess(by[s], prim, True) for s in HIST}
    q = quantities(per)
    ps = {k: tstats(v) for k, v in q.items()}
    report["primary"] = ps
    report["primary_by_group"] = {G: tstats([per[s][G] for s in HIST if G in per[s]])
                                  for G in GROUPS if G in per[HIST[0]]}
    report["label_part1"] = label_part1(ps["E_SEC"], ps["D_PWR"])
    report["label_part2"] = label_part2(ps["D_ACC"])

    gate = {}
    for nm, *_ in variants():
        p = {s: season_excess(by[s], f"sor_{nm}", True) for s in HIST}
        gate[f"SOR {nm}"] = {k: float(np.mean(v)) for k, v in quantities(p).items()}
    p = {s: season_excess(by[s], prim, True, use="pts") for s in HIST}
    gate["rank points"] = {k: float(np.mean(v)) for k, v in quantities(p).items()}
    p = {s: season_excess(by[s], "colley", False) for s in HIST}
    gate["Colley top 25"] = {k: float(np.mean(v)) for k, v in quantities(p).items()}
    fore = {}
    for s in HIST:
        full = allw[allw.season == s]
        fore[s] = season_excess(by[s], prim, True, foresight=full[full.week == full.week.max()])
    gate["end-of-season SOR (foresight)"] = {k: float(np.mean(v)) for k, v in quantities(fore).items()}
    robust = gate_summary(gate, {k: ps[k]["mean"] for k in ("E_SEC", "D_PWR", "D_ACC")})
    report["robustness_gate"] = {"by_check": gate, "summary": robust,
                                 **gate_verdict(robust, report["label_part1"], report["label_part2"])}

    # Secondary: committee minus AP in the same label week.
    pa = {s: season_excess(by[s], "ap_same_week", True) for s in HIST}
    qa = quantities(pa)
    report["committee_minus_ap"] = {
        "C_" + k.split("_")[1]: tstats(v) for k, v in qa.items()}
    report["committee_minus_ap_by_group"] = {G: float(np.mean([pa[s][G] for s in HIST if G in pa[s]]))
                                             for G in GROUPS}
    report["committee_minus_ap_label_part1"] = label_part1(report["committee_minus_ap"]["C_SEC"],
                                                           report["committee_minus_ap"]["C_PWR"])
    report["committee_minus_ap_label_part2"] = label_part2(report["committee_minus_ap"]["C_ACC"])

    # Descriptive: the bubble, places 6-16.
    pb = {s: bubble_excess(by[s], f"sor_rank_{PRIMARY[0]}|x{PRIMARY[1]}") for s in HIST}
    report["bubble_places_6_16_descriptive"] = {k: tstats(v) for k, v in quantities(pb).items()}

    # Levels, for context: committee top-25 slots per ranking by group.
    lev = {}
    for s in HIST:
        for _, d in by[s].groupby("week"):
            sl = shares(d.set_index("team").ap_rank)[0]
            g = d.set_index("team").group
            for G in GROUPS:
                lev.setdefault(G, []).append(float(sl[g == G].sum()))
    report["committee_slots_per_ranking"] = {G: float(np.mean(v)) for G, v in lev.items()}

    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    for k in ("E_SEC", "D_PWR", "D_ACC"):
        v = ps[k]
        print(f"  {k}: {v['mean']:+.2f} (95% t {v['ci95_t'][0]:+.2f} to {v['ci95_t'][1]:+.2f}; "
              f"{v['seasons_positive']}/11; p {v['sign_flip_p']:.3f})")
    print("  label 1:", report["label_part1"], "| robust:", report["robustness_gate"]["label_part1_robust"])
    print("  label 2:", report["label_part2"], "| robust:", report["robustness_gate"]["label_part2_robust"])
    for k, v in report["committee_minus_ap"].items():
        print(f"  {k}: {v['mean']:+.2f} (95% t {v['ci95_t'][0]:+.2f} to {v['ci95_t'][1]:+.2f}; "
              f"{v['seasons_positive']}/11)")
    print("  unmatched committee schools:", unmatched)


if __name__ == "__main__":
    main()
