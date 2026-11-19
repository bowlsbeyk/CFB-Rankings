"""2026 "ranked wins" against results (DEVIATIONS.md, 2026-11-19; descriptive).

For each 2026 regular-season FBS-vs-FBS game through the frozen week, the opponent's AP rank on game
day (poll released before that week's games) and its strength-of-record rank now. Summaries by the
team's conference group. Writes results/ranked_wins_2026.json and results/ranked_wins_2026.csv.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sor_test import group_of  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RES = ROOT / "results"


def main():
    sor = pd.read_csv(RES / "sor_2026.csv").set_index("team")
    last = int(json.loads((RES / "post_numbers.json").read_text())["miami_2026"]["after_week"])
    polls = {}
    for w in json.loads((RAW / "polls" / "rankings_2026_regular.json").read_text()):
        for p in w["polls"]:
            if p["poll"] == "AP Top 25":
                polls[w["week"]] = {r["school"]: r["rank"] for r in p["ranks"]}
    g = pd.read_parquet(RAW / "schedules" / "cfb_schedules_2026.parquet")
    g = g[(g.season_type == "regular") & g.completed & (g.week <= last)
          & (g.home_division == "fbs") & (g.away_division == "fbs")]
    rows = []
    for x in g.itertuples():
        for team, conf, opp, pf, pa in ((x.home_team, x.home_conference, x.away_team, x.home_points, x.away_points),
                                        (x.away_team, x.away_conference, x.home_team, x.away_points, x.home_points)):
            rows.append({"week": x.week, "team": team, "group": group_of(conf, team, 2026), "opponent": opp,
                         "won": pf > pa, "opp_gameday_ap": polls.get(x.week, {}).get(opp),
                         "opp_sor_now": sor.sor_rank.get(opp), "opp_ap_now": sor.ap_rank.get(opp)})
    d = pd.DataFrame(rows)
    d.to_csv(RES / "ranked_wins_2026.csv", index=False)
    ranked = d[d.opp_gameday_ap.notna()]
    out = {"after_week": last, "note": "descriptive; FBS vs FBS regular-season games; strength-of-record rank after the last frozen week"}
    for G, x in ranked.groupby("group"):
        w, l = x[x.won], x[~x.won]
        out[G] = {"games_vs_gameday_ranked": int(len(x)),
                  "ranked_wins": int(len(w)), "ranked_wins_opponent_now_sor_top25": int((w.opp_sor_now <= 25).sum()),
                  "ranked_losses": int(len(l)), "ranked_losses_opponent_now_sor_top25": int((l.opp_sor_now <= 25).sum()),
                  "share_of_ranked_opponents_now_outside_sor_top25": round(float((x.opp_sor_now > 25).mean()), 3)}
    (RES / "ranked_wins_2026.json").write_text(json.dumps(out, indent=2) + "\n")
    for G in ("SEC", "ACC", "Big Ten", "Big 12", "Other", "Notre Dame"):
        if G in out:
            o = out[G]
            print(f"{G:10s} vs ranked {o['games_vs_gameday_ranked']:3d}: wins {o['ranked_wins']:2d} "
                  f"({o['ranked_wins_opponent_now_sor_top25']} still SOR top 25), losses {o['ranked_losses']:2d} "
                  f"({o['ranked_losses_opponent_now_sor_top25']}), share now outside {o['share_of_ranked_opponents_now_outside_sor_top25']:.0%}")
    sec_ranked = ranked[(ranked.group == "SEC")]
    print(sec_ranked[sec_ranked.opp_sor_now > 25][["week", "team", "opponent", "won", "opp_gameday_ap", "opp_sor_now", "opp_ap_now"]].to_string(index=False))


if __name__ == "__main__":
    main()
