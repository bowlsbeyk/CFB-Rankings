"""T3: the in-season "ranked loop" (DEVIATIONS.md, 2026-10-23; added after earlier results).

For ranked teams' games, post-game overrating = final season-only rank (capped at 26)
minus AP rank in the poll right after the game (26 if unranked). Positive = after the
game the poll ranked the team above where its season ended up. Adjusted for the
pre-game AP rank with a straight-line fit across all conferences, per group:

  primary  lost to a ranked opponent from the same conference (the loop's losing side)
  C1       lost to a ranked opponent from another conference
  C2       lost to an unranked opponent
  winners  beat a ranked opponent from the same conference (the loop's winning side)

95% intervals: 1,000 resamples of team-seasons (seed 0). Writes results/t3_loop.json and
every qualifying game to results/t3_loop_games.csv.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
RATINGS = ROOT / "data" / "processed" / "season_ratings.csv"
OUT = ROOT / "results" / "t3_loop.json"
GAMES = ROOT / "results" / "t3_loop_games.csv"
SEASONS = [s for s in range(2014, 2026) if s != 2020]
CONFS = ["SEC", "ACC", "Big Ten", "Big 12", "Other"]
GROUPS = {
    "primary_lost_to_ranked_same_conference": "Lost to a ranked opponent from the same conference",
    "C1_lost_to_ranked_other_conference": "Lost to a ranked opponent from another conference",
    "C2_lost_to_unranked": "Lost to an unranked opponent",
    "winners_beat_ranked_same_conference": "Beat a ranked opponent from the same conference",
}
N_BOOT = 1000


def ci(x):
    return [float(v) for v in np.percentile(x, [2.5, 97.5])]


def qualifying_games(tw, ratings):
    last = ratings.groupby("season").week.transform("max") == ratings.week
    final = ratings[last].set_index(["season", "team"]).strength_rank
    rank_before = tw.set_index(["season", "week", "team"]).prior_rank
    conf = tw.drop_duplicates(["season", "team"]).set_index(["season", "team"]).conference

    g = tw[tw.prior_rank.notna() & (tw.games == 1)].copy()
    g["opponent"] = g.opponents
    g["opp_conference"] = [conf.get((s, o), "FCS") for s, o in zip(g.season, g.opponent)]
    g["opp_rank_before"] = [rank_before.get((s, w, o), np.nan) for s, w, o in zip(g.season, g.week, g.opponent)]
    g["result"] = np.where(g.wins == 1, "W", "L")
    g["rank_before"] = g.prior_rank
    g["rank_after"] = g.next_rank.fillna(26)
    g["final_results_rank"] = [final.get((s, t), np.nan) for s, t in zip(g.season, g.team)]
    g["overrating"] = g.final_results_rank.clip(upper=26) - g.rank_after
    same = g.conference == g.opp_conference
    opp_ranked = g.opp_rank_before.notna()
    lost = g.result == "L"
    g["group"] = np.select(
        [lost & opp_ranked & same, lost & opp_ranked & ~same, lost & ~opp_ranked, ~lost & opp_ranked & same],
        list(GROUPS), default="")
    g = g[g.group != ""].copy()
    g["adjusted"] = np.nan
    for grp in GROUPS:
        m = g.group == grp
        slope, intercept = np.polyfit(g.loc[m, "rank_before"], g.loc[m, "overrating"], 1)
        g.loc[m, "adjusted"] = g.loc[m, "overrating"] - (intercept + slope * g.loc[m, "rank_before"])
    g["places_moved"] = g.rank_before - g.rank_after
    return g


def boot_means(df, rng):
    """Per-team-season sums/counts, resampled; returns (point mean, bootstrap means)."""
    per = df.groupby(["season", "team"]).adjusted.agg(["sum", "count"])
    s, n = per["sum"].to_numpy(), per["count"].to_numpy()
    idx = rng.integers(0, len(per), size=(N_BOOT, len(per)))
    return float(s.sum() / n.sum()), s[idx].sum(1) / n[idx].sum(1)


def main():
    tw = pd.read_csv(TABLE)
    tw = tw[tw.season.isin(SEASONS)]
    g = qualifying_games(tw, pd.read_csv(RATINGS))
    rng = np.random.default_rng(0)
    report = {}
    boots = {}
    for grp, label in GROUPS.items():
        gg = g[g.group == grp]
        block = {"description": label, "games": int(len(gg))}
        for c in CONFS:
            gc = gg[gg.conf_group == c]
            if len(gc) == 0:
                continue
            m, b = boot_means(gc, rng)
            boots[(grp, c)] = b
            block[c] = {"games": int(len(gc)), "adjusted_overrating": m, "ci": ci(b),
                        "raw_overrating": float(gc.overrating.mean()),
                        "share_still_ranked_next_poll": float((gc.next_rank.notna()).mean()),
                        "mean_places_moved": float(gc.places_moved.mean())}
        if ("SEC" in block) and ("ACC" in block):
            block["sec_minus_acc"] = block["SEC"]["adjusted_overrating"] - block["ACC"]["adjusted_overrating"]
            block["sec_minus_acc_ci"] = ci(boots[(grp, "SEC")] - boots[(grp, "ACC")])
        report[grp] = block

    # SEC primary minus SEC C1: resample SEC team-seasons jointly across both groups.
    sec = g[(g.conf_group == "SEC") & g.group.isin(["primary_lost_to_ranked_same_conference",
                                                     "C1_lost_to_ranked_other_conference"])]
    units = sec.groupby(["season", "team"])
    keys = list(units.groups)
    pos = {k: i for i, k in enumerate(keys)}
    sums = np.zeros((len(keys), 2))
    cnts = np.zeros((len(keys), 2))
    for _, r in sec.iterrows():
        j = 0 if r.group.startswith("primary") else 1
        sums[pos[(r.season, r.team)], j] += r.adjusted
        cnts[pos[(r.season, r.team)], j] += 1
    idx = np.random.default_rng(0).integers(0, len(keys), size=(N_BOOT, len(keys)))
    diff = sums[idx][:, :, 0].sum(1) / cnts[idx][:, :, 0].sum(1) - sums[idx][:, :, 1].sum(1) / cnts[idx][:, :, 1].sum(1)
    point = sums[:, 0].sum() / cnts[:, 0].sum() - sums[:, 1].sum() / cnts[:, 1].sum()
    report["sec_primary_minus_sec_C1"] = {"diff": float(point), "ci": ci(diff)}

    p = report["primary_lost_to_ranked_same_conference"]
    sec_pos = p["SEC"]["ci"][0] > 0
    gap_pos = p.get("sec_minus_acc_ci", [0])[0] > 0
    report["reading"] = "supports" if sec_pos and gap_pos else "partial" if sec_pos else "not supported"
    report["note"] = ("adjusted_overrating: places the poll ranked the team above its final season-only "
                      "rank right after the game, beyond what is typical for its pre-game rank. "
                      "Positive = stayed ranked above where its season ended up.")
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    cols = ["season", "week", "team", "conference", "opponent", "opp_conference", "result", "points_for",
            "points_against", "rank_before", "opp_rank_before", "rank_after", "final_results_rank",
            "overrating", "adjusted", "group"]
    g.sort_values(["season", "week", "team"])[cols].round(3).to_csv(GAMES, index=False)

    print(f"T3 reading: {report['reading']}")
    for grp in GROUPS:
        b = report[grp]
        print(f"{b['description']} ({b['games']} games)")
        for c in CONFS:
            if c in b:
                x = b[c]
                print(f"   {c:8} n={x['games']:3} adjusted {x['adjusted_overrating']:+.2f} ({x['ci'][0]:+.2f}, {x['ci'][1]:+.2f})"
                      f"  raw {x['raw_overrating']:+.2f}  still ranked {x['share_still_ranked_next_poll']:.0%}"
                      f"  moved {x['mean_places_moved']:+.1f}")
        if "sec_minus_acc" in b:
            print(f"   SEC-ACC {b['sec_minus_acc']:+.2f} ({b['sec_minus_acc_ci'][0]:+.2f}, {b['sec_minus_acc_ci'][1]:+.2f})")
    d = report["sec_primary_minus_sec_C1"]
    print(f"SEC primary minus SEC C1: {d['diff']:+.2f} ({d['ci'][0]:+.2f}, {d['ci'][1]:+.2f})")


if __name__ == "__main__":
    main()
