"""Post-hoc plausibility check on the counterfactual (added after seeing it; DEVIATIONS.md).

What real AP voters did at poll 8 (after 7 weeks), 2014-2025 (no 2020), for the
situations the 2026 swap creates: strong records that started unranked, and
weak records that started ranked. Real data only; no model.
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
OUT = ROOT / "results" / "base_rates_poll8.json"
P4 = ["SEC", "ACC", "Big Ten", "Big 12"]


def main():
    tw = pd.read_csv(TABLE)
    h = tw[tw.season <= 2025]
    pre = h[h.week == 1].set_index(["season", "team"]).prior_rank
    h = h.assign(pre_rank=h.set_index(["season", "team"]).index.map(pre))
    w = h[h.week == 7]
    p4 = w.conf_group.isin(P4)
    strong = (w.wins_to_date >= 6) & (w.losses_to_date <= 1)
    good = (w.wins_to_date >= 5) & (w.losses_to_date <= 1)
    cases = {
        "P4, started unranked, 6-1 or better": p4 & w.pre_rank.isna() & strong,
        "P4, started ranked, 6-1 or better": p4 & w.pre_rank.notna() & strong,
        "P4, started unranked, 5-1 or better": p4 & w.pre_rank.isna() & good,
        "P4, started ranked, 5-1 or better": p4 & w.pre_rank.notna() & good,
        "Started top 12, 3+ losses": w.pre_rank.le(12) & (w.losses_to_date >= 3),
        "Started 13-25, 3+ losses": w.pre_rank.between(13, 25) & (w.losses_to_date >= 3),
        "Started unranked, 3+ losses": w.pre_rank.isna() & (w.losses_to_date >= 3),
    }
    out = {k: {"team_seasons": int(sel.sum()),
               "ranked_in_poll_8": float(w[sel].next_rank.notna().mean())}
           for k, sel in cases.items()}
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    for k, v in out.items():
        print(f"{k:40} {v['team_seasons']:4}  ranked {v['ranked_in_poll_8']:.0%}")


if __name__ == "__main__":
    main()
