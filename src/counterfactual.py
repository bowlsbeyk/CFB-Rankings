"""2026 counterfactual: swap SEC and ACC preseason slots, replay real results.

Runs (each under both unranked rules; 0 rule is primary):
  sanity   no swap; its drift from the real poll is the model's error bar

Usage: python src/counterfactual.py [revised|rated]   (default revised)
  swap3    primary: the 3 ranked ACC teams swap with the top 3 SEC teams
  swap9    extension: all 9 ranked SEC slots go to ACC teams, unranked teams
           ordered by preseason Elo (pairing only; DEVIATIONS.md)

For each paired team: real rank, simulated rank without the swap, simulated
rank with it, for every completed 2026 poll. Gain = no-swap rank - swap rank
(positive = the swap moved the team up). Ranks are capped at 26 (= unranked).
A gain no larger than the stickiness yardstick is reported as indistinguishable
from model inertia.
"""

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from replay import compare, real_poll, replay, start_values

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
RESULTS = ROOT / "results"
SEASON = 2026
P4 = ["SEC", "ACC", "Big Ten", "Big 12"]


def yardstick(spec, treatment):
    """Larger of training-replay stickiness and holdout mean (DEVIATIONS.md)."""
    train = json.loads((RESULTS / "replay_training.json").read_text())
    tr_val = train[f"{spec}_gbt_{treatment}"]["summary"]["stickiness_spots_mean"]
    hold_file = "holdout.json" if spec != "rated" else "holdout_reuse_rated.json"
    hold = json.loads((RESULTS / hold_file).read_text())[f"{spec}_{treatment}"]["replay"]
    hold_val = np.mean([hold[s]["stickiness"]["spots_kept_above_real"] for s in hold])
    return round(float(max(tr_val, hold_val)), 2)


def plausibility(sim_rank, last_rows, conf_of):
    """Pre-set check against real voters (DEVIATIONS.md): strong P4 records left
    unranked, and teams with 3+ losses ranked, in the simulated poll."""
    top = set(sim_rank.nsmallest(25).index)
    r = last_rows.set_index("team")
    strong = r[r.conf_group.isin(P4) & (((r.losses_to_date == 0) & (r.wins_to_date >= 5))
                                        | ((r.losses_to_date == 1) & (r.wins_to_date >= 6)))]
    weak = r[r.losses_to_date >= 3]
    left_out = sorted(t for t in strong.index if t not in top)
    ranked_weak = sorted(t for t in weak.index if t in top)
    return {"strong_p4_records": int(len(strong)), "strong_left_unranked": left_out,
            "three_plus_losses": int(len(weak)), "three_plus_losses_ranked": ranked_weak,
            "plausible": not left_out and not ranked_weak}


def preseason_elo(rows):
    first = rows.dropna(subset=["elo"]).sort_values("week").drop_duplicates("team")
    return first.set_index("team").elo


def ordered(conf, start, elo, conf_of):
    teams = [t for t in conf_of.index if conf_of[t] == conf]
    return sorted(teams, key=lambda t: (-start.get(t, 0.0), -elo.get(t, -np.inf), t))


def make_pairs(start, elo, conf_of, mode):
    sec = ordered("SEC", start, elo, conf_of)
    acc = ordered("ACC", start, elo, conf_of)
    n_ranked = {c: sum(1 for t in lst if start.get(t, 0) > 0)
                for c, lst in (("SEC", sec), ("ACC", acc))}
    n = min(n_ranked.values()) if mode == "swap3" else max(n_ranked.values())
    return list(zip(sec[:n], acc[:n]))


def capped(sim_rank):
    return sim_rank.clip(upper=26)


def conf_slots(teams_top25, conf_of):
    s = pd.Series([conf_of.get(t, "Other") for t in teams_top25]).value_counts()
    return {c: int(s.get(c, 0)) for c in ("SEC", "ACC", "Big Ten", "Big 12", "Other")}


def run(treatment, spec):
    tw = pd.read_csv(TABLE)
    rows = tw[tw.season == SEASON]
    conf_of = rows.drop_duplicates("team").set_index("team").conf_group
    model = joblib.load(RESULTS / "models" / f"gbt_{spec}_{treatment}.joblib")
    start = start_values(SEASON, spec)
    last_rows = rows[rows.week == rows.week.max()]
    ystick = yardstick(spec, treatment)
    elo = preseason_elo(rows)

    base = replay(rows, model, treatment, start, spec)
    weeks = sorted(base)
    real = {w: real_poll(SEASON, w) for w in weeks}
    out = {"spec": spec, "yardstick_spots": ystick,
           "plausibility_no_swap": plausibility(base[weeks[-1]].sim_rank, last_rows, conf_of),
           "sanity": {str(w): compare(base[w].sim_rank, real[w]) for w in weeks},
           "conference_slots": {"real": {str(w): conf_slots(real[w], conf_of) for w in weeks},
                                "no_swap": {str(w): conf_slots(base[w].sim_rank.nsmallest(25).index,
                                                               conf_of) for w in weeks}}}

    for mode in ("swap3", "swap9"):
        pairs = make_pairs(start, elo, conf_of, mode)
        swapped = dict(start)
        for s, a in pairs:
            swapped[s], swapped[a] = start.get(a, 0.0), start.get(s, 0.0)
        swapped = {t: p for t, p in swapped.items() if p > 0}
        sim = replay(rows, model, treatment, swapped, spec)
        teams = []
        for s, a in pairs:
            for team, partner in ((s, a), (a, s)):
                weekly = []
                for w in weeks:
                    real_rank = real[w][team]["rank"] if team in real[w] else 26
                    nb, sw = capped(base[w].sim_rank)[team], capped(sim[w].sim_rank)[team]
                    weekly.append({"poll_week": w, "real": real_rank, "no_swap": float(nb),
                                   "swap": float(sw), "gain": float(nb - sw)})
                final = weekly[-1]
                teams.append({
                    "team": team, "conference": conf_of[team], "partner": partner,
                    "preseason_points_real": start.get(team, 0.0),
                    "preseason_points_swapped": swapped.get(team, 0.0),
                    "final_gain": final["gain"],
                    "beyond_yardstick": abs(final["gain"]) > ystick,
                    "weekly": weekly})
        out[mode] = {
            "pairs": pairs,
            "teams": teams,
            "conference_slots": {str(w): conf_slots(sim[w].sim_rank.nsmallest(25).index, conf_of)
                                 for w in weeks},
            "plausibility": plausibility(sim[weeks[-1]].sim_rank, last_rows, conf_of),
        }
    return out


def main():
    spec = sys.argv[1] if len(sys.argv) > 1 else "revised"
    report = {tr: run(tr, spec) for tr in ("zero", "floor")}
    report["note"] = ("2026 regular season through the latest completed poll. Primary: 0 rule, "
                      "swap3. Ranks capped at 26 (= unranked).")
    name = "counterfactual_2026.json" if spec == "revised" else f"counterfactual_2026_{spec}.json"
    (RESULTS / name).write_text(json.dumps(report, indent=2) + "\n")

    for tr in ("zero", "floor"):
        r = report[tr]
        last = max(r["sanity"], key=int)
        s = r["sanity"][last]
        print(f"\n[{tr}] sanity (no swap) vs real, poll {last}: Spearman {s['spearman']:.2f}, "
              f"overlap {s['overlap']}/25, mean rank error {s['mean_abs_rank_error']:.1f}; "
              f"yardstick {r['yardstick_spots']} spots")
        print(f"  top-25 slots poll {last}: real {r['conference_slots']['real'][last]} | "
              f"no swap {r['conference_slots']['no_swap'][last]}")
        p = r["plausibility_no_swap"]
        print(f"  plausibility (no swap): strong left out {p['strong_left_unranked']}, "
              f"3+ losses ranked {p['three_plus_losses_ranked']}")
        for mode in ("swap3", "swap9"):
            p = r[mode]["plausibility"]
            print(f"  {mode}: slots {r[mode]['conference_slots'][last]} | plausible: {p['plausible']}"
                  f" (strong left out {p['strong_left_unranked']}, "
                  f"3+ losses ranked {p['three_plus_losses_ranked']})")
            for t in r[mode]["teams"]:
                f = t["weekly"][-1]
                print(f"    {t['team']:18} {t['conference']:4} (pair {t['partner']:16}) "
                      f"real {f['real']:>4}  no-swap {f['no_swap']:>4.0f}  swap {f['swap']:>4.0f}  "
                      f"gain {f['gain']:+5.1f}{'  *' if t['beyond_yardstick'] else ''}")


if __name__ == "__main__":
    main()
