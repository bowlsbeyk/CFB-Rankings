"""T5: is the SEC ranked so high because of its results? (DEVIATIONS.md, 2026-10-31.)

Ranking-independent measures, rebuilt after every week from that season's scores,
home/away/neutral site and who played whom (no polls, preseason, prior seasons, names or
conference labels; FCS opponents pooled as one team):
  performance  margin-based rating (the season-only performance component)
  Colley       wins-and-losses rating (the season-only results component; no margins)
  SOR          strength of record: the probability that a benchmark team (mean of the 25
               best by performance that week) would win at least as many of a team's games
               as it did, against the same opponents at the same venues (Poisson-binomial,
               win chance = Phi((benchmark - opponent + home edge * venue) / sigma)).
               Lower = more impressive.

Conference is used only to count teams after the rankings are built (and in the labelled
T4-offset check). Compares AP top-25 slots with SOR top-25 slots by group, 2014-2025, plus
2026 to date. Definitions, reading and robustness gate: DEVIATIONS.md.

Writes results/t5_sor.json, results/sor_weekly.csv (every team-week's derived ranks, no
poll data) and results/sor_2026.csv.
"""

import io
import itertools
import json
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, t as tdist

from build_features import load_games
from season_rating import colley

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "team_weeks.csv"
RATINGS = ROOT / "data" / "processed" / "season_ratings.csv"
T4 = ROOT / "results" / "t4_referee.json"
OUT = ROOT / "results" / "t5_sor.json"
WEEKLY = ROOT / "results" / "sor_weekly.csv"
OUT_2026 = ROOT / "results" / "sor_2026.csv"

HIST = [s for s in range(2014, 2026) if s != 2020]
SEASONS = HIST + [2026]
FCS = "FCS (pooled)"
CAP = 28
SIGMA = 14.102          # no-intercept probit scale, FBS vs FBS week 4+, 2014-2025 (fixed)
FIRST_WEEK = 5          # schedule week 5 -> AP poll 6
SIGMA_MULT = (0.75, 1.0, 1.25)
BENCHES = ("top12", "top25", "rank25")
PRIMARY = ("top25", 1.0)
GROUPS = ["SEC", "ACC", "Big Ten", "Big 12", "Pac-12", "Notre Dame", "Other"]
POWER_OTHERS = ["ACC", "Big Ten", "Big 12", "Pac-12"]
BAND = 0.5              # equivalence band, slots per poll
N_SIM = 200
N_BOOT = 1000


# ----------------------------------------------------------------- inputs

def group_of(conference, team, season):
    if team == "Notre Dame":
        return "Notre Dame"
    if conference in ("SEC", "ACC", "Big Ten", "Big 12"):
        return conference
    if conference == "Pac-12" and season <= 2023:
        return "Pac-12"
    return "Other"


def season_games(season):
    with redirect_stdout(io.StringIO()):
        g = load_games(season)
    g = g.copy()
    # A game kicking off Sunday 2 pm ET or later in week 2+ comes after that week's AP poll;
    # it counts from the next week (on this data: 2016 Georgia at South Carolina only).
    et = pd.to_datetime(g.start_date, utc=True).dt.tz_convert("America/New_York")
    late = (et.dt.dayofweek == 6) & (et.dt.hour >= 14) & (g.week >= 2)
    g.loc[late, "week"] = g.loc[late, "week"] + 1
    g["home"] = np.where(g.home_division == "fbs", g.home_team, FCS)
    g["away"] = np.where(g.away_division == "fbs", g.away_team, FCS)
    g["margin"] = (g.home_points - g.away_points).astype(float)
    return g.reset_index(drop=True), int(late.sum())


def performance_fast(hi, ai, home, margin, n):
    """Same least-squares rating as season_rating.performance, vectorized.
    Returns (ratings[n], home_edge)."""
    m = len(hi)
    A = np.zeros((m + n, n + 1))
    A[np.arange(m), hi] = 1.0
    A[np.arange(m), ai] = -1.0
    A[np.arange(m), n] = home
    A[m + np.arange(n), np.arange(n)] = 1.0
    y = np.concatenate([np.clip(margin, -CAP, CAP), np.zeros(n)])
    sol = np.linalg.lstsq(A, y, rcond=None)[0]
    return sol[:n], float(sol[n])


# ----------------------------------------------------------------- SOR

def sor_probs(opp, venue, won_count, mask, r, h, bench, sigma):
    """Vectorized SOR: P(benchmark wins >= wins) for every team.
    opp/venue/mask: (teams, max_games) arrays; won_count: (teams,)."""
    p = norm.cdf((bench - r[opp] + h * venue) / sigma) * mask
    n_t, g = p.shape
    dist = np.zeros((n_t, g + 1))
    dist[:, 0] = 1.0
    for j in range(g):
        pj = p[:, j:j + 1]
        dist[:, 1:] = dist[:, 1:] * (1 - pj) + dist[:, :-1] * pj
        dist[:, 0] *= (1 - p[:, j])
    cum = np.cumsum(dist[:, ::-1], axis=1)[:, ::-1]  # cum[:, k] = P(X >= k)
    return cum[np.arange(n_t), won_count]


def bench_value(perf_fbs, kind):
    top = np.sort(perf_fbs)[::-1]
    return {"top12": top[:12].mean(), "top25": top[:25].mean(), "rank25": top[24]}[kind]


def schedule_arrays(games, teams, fbs_idx):
    """Per FBS team: opponent indices, venues, win flags for the given games."""
    idx = {t: i for i, t in enumerate(teams)}
    hi = games.home.map(idx).to_numpy()
    ai = games.away.map(idx).to_numpy()
    venue_h = np.where(games.neutral_site.to_numpy(), 0, 1)
    rows = {i: [] for i in fbs_idx}
    for k in range(len(games)):
        h_, a_, v_, mg = hi[k], ai[k], venue_h[k], games.margin.iat[k]
        if h_ in rows:
            rows[h_].append((a_, v_, int(mg > 0)))
        if a_ in rows:
            rows[a_].append((h_, -v_, int(mg < 0)))
    g = max(len(v) for v in rows.values()) or 1
    n_t = len(fbs_idx)
    opp = np.zeros((n_t, g), dtype=int)
    ven = np.zeros((n_t, g))
    mask = np.zeros((n_t, g))
    wins = np.zeros(n_t, dtype=int)
    for j, i in enumerate(fbs_idx):
        for c, (o, v, w) in enumerate(rows[i]):
            opp[j, c], ven[j, c], mask[j, c] = o, v, 1.0
            wins[j] += w
    return opp, ven, mask, wins, hi, ai


# ----------------------------------------------------------------- slots and points

def shares(key, limit=25):
    """Top-`limit` slot share and rank points per team from a key where lower is better
    (NaN = outside). Ties: each of k teams tied over places a..b gets the share of those
    places inside the top `limit` and the mean of max(0, 26 - place)."""
    s = key.dropna().sort_values(kind="mergesort")
    slot = pd.Series(0.0, index=key.index)
    pts = pd.Series(0.0, index=key.index)
    vals = s.to_numpy()
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[j + 1] == vals[i]:
            j += 1
        places = np.arange(i + 1, j + 2)
        ids = s.index[i:j + 1]
        slot[ids] = np.mean(places <= limit)
        pts[ids] = np.mean(np.maximum(0, 26 - places)) if limit == 25 else 0.0
        i = j + 1
    return slot, pts


# ----------------------------------------------------------------- statistics

def tstats(values):
    v = np.asarray(values, dtype=float)
    n = len(v)
    m, sd = v.mean(), v.std(ddof=1)
    se = sd / np.sqrt(n)
    ci95 = [m - tdist.ppf(0.975, n - 1) * se, m + tdist.ppf(0.975, n - 1) * se]
    ci90 = [m - tdist.ppf(0.95, n - 1) * se, m + tdist.ppf(0.95, n - 1) * se]
    flips = np.array(list(itertools.product([1, -1], repeat=n)))
    null = np.abs((flips * v).mean(axis=1))
    p = float(np.mean(null >= abs(m) - 1e-12))
    return {"mean": float(m), "ci95_t": [float(x) for x in ci95], "ci90_t": [float(x) for x in ci90],
            "seasons_positive": int((v > 0).sum()), "seasons": n, "sign_flip_p": p,
            "per_season": [float(x) for x in v]}


def boot_seasons(values, seed=0):
    v = np.asarray(values, dtype=float)
    idx = np.random.default_rng(seed).integers(0, len(v), size=(N_BOOT, len(v)))
    return [float(x) for x in np.percentile(v[idx].mean(1), [2.5, 97.5])]


def label_part1(e, dpwr):
    over = e["ci95_t"][0] > 0 and e["seasons_positive"] >= 9
    consistent = e["ci90_t"][0] >= -BAND and e["ci90_t"][1] <= BAND
    under = e["ci95_t"][1] < 0 and e["seasons_positive"] <= 2
    specific = dpwr["ci95_t"][0] > 0 and dpwr["seasons_positive"] >= 9
    if over and consistent:
        return "over-ranked by less than half a slot per poll" + ("" if specific else
               " (shared with the other power conferences, not SEC-specific)")
    if over:
        return "OVER-RANKED, " + ("SEC-SPECIFIC" if specific else
                                  "SHARED WITH THE OTHER POWER CONFERENCES, NOT SEC-SPECIFIC")
    if consistent:
        return "CONSISTENT WITH RESULTS"
    if under:
        return "UNDER-RANKED"
    return "INCONCLUSIVE"


def label_part2(d):
    if d["ci95_t"][0] > 0 and d["seasons_positive"] >= 9:
        return "SEC excess HIGHER than ACC"
    if d["ci95_t"][1] < 0 and d["seasons_positive"] <= 2:
        return "SEC excess LOWER than ACC"
    return "INCONCLUSIVE"


# ----------------------------------------------------------------- per-season engine

def offsets_from_t4():
    t4 = json.loads(T4.read_text())
    all_ = {c: t4[c]["all"]["mean_residual"] for c in ["SEC", "ACC", "Big Ten", "Big 12", "Pac-12"]}
    pwr = {c: t4[c]["vs_power_opponents"]["mean_residual"] for c in ["SEC", "ACC", "Big Ten", "Big 12", "Pac-12"]}
    return {"t4_all": all_, "t4_power": pwr}


def variants():
    v = [(f"{b}|x{m}", b, m, None) for b in BENCHES for m in SIGMA_MULT]
    v += [(f"top25|x1.0|{o}", "top25", 1.0, o) for o in ("t4_all", "t4_power")]
    return v


def run_season(season, tw, offsets):
    games, n_late = season_games(season)
    teams = sorted((set(games.home) | set(games.away)) - {FCS}) + [FCS]
    n = len(teams)
    fbs_idx = list(range(n - 1))
    fbs = teams[:-1]
    s_tw = tw[tw.season == season]
    conf = s_tw.drop_duplicates("team").set_index("team").conference
    grp = pd.Series({t: group_of(conf.get(t, "FCS"), t, season) for t in fbs})
    last_w = int(s_tw.week.max())
    weeks = [w for w in range(FIRST_WEEK, last_w + 1)] if season != 2026 else [last_w]
    ap_next = s_tw.set_index(["week", "team"]).next_rank
    rows = []
    for w in weeks:
        played = games[games.week <= w]
        opp, ven, mask, wins, hi, ai = schedule_arrays(played, teams, fbs_idx)
        home = np.where(played.neutral_site.to_numpy(), 0.0, 1.0)
        r, h = performance_fast(hi, ai, home, played.margin.to_numpy(), n)
        col = colley(played, teams)
        base = {"season": season, "week": w, "team": fbs, "group": grp[fbs].to_numpy(),
                "wins": wins, "losses": mask.sum(1).astype(int) - wins,
                "performance": r[:-1], "colley": col[fbs].to_numpy()}
        for name, bench, mult, off in variants():
            rr = r.copy()
            if off:
                rr[:-1] = rr[:-1] + grp[fbs].map(offsets[off]).fillna(0.0).to_numpy()
            b = bench_value(rr[:-1], bench)
            base[f"sor_{name}"] = sor_probs(opp, ven, wins, mask, rr, h, b, SIGMA * mult)
            if off:
                base[f"perf_{off}"] = rr[:-1]
        d = pd.DataFrame(base)
        d["ap_rank"] = [ap_next.get((w, t), np.nan) for t in fbs]
        rows.append(d)
    return pd.concat(rows, ignore_index=True), games, teams, grp, last_w, n_late


def poll_counts(d, key_col, ascending, limit=25):
    """Per-poll AP and measure slots/points by group for one week's frame d."""
    key = d.set_index("team")[key_col]
    key = key if ascending else -key
    m_slot, m_pts = shares(key, limit)
    a_slot, a_pts = shares(d.set_index("team").ap_rank, limit)
    g = d.set_index("team").group
    out = {}
    for G in GROUPS:
        sel = g == G
        if not sel.any():
            continue
        out[G] = {"ap_slots": float(a_slot[sel].sum()), "m_slots": float(m_slot[sel].sum()),
                  "ap_pts": float(a_pts[sel].sum()), "m_pts": float(m_pts[sel].sum()),
                  "members": int(sel.sum())}
    return out


def season_excess(frames, key_col, ascending, use="slots", foresight=None):
    """Mean over polls of AP minus measure (slots or rank points), by group, one season."""
    acc = {}
    for w, d in frames.groupby("week"):
        if foresight is not None:
            d = d.drop(columns=[key_col]).merge(foresight[["team", key_col]], on="team")
        c = poll_counts(d, key_col, ascending)
        for G, x in c.items():
            acc.setdefault(G, []).append(x[f"ap_{use}"] - x[f"m_{use}"])
    return {G: float(np.mean(v)) for G, v in acc.items()}


def quantities(per_season):
    """E_SEC, D_PWR, D_ACC per season from {season: {group: excess}}."""
    e, dp, da = [], [], []
    for s in HIST:
        x = per_season[s]
        others = [x[G] for G in POWER_OTHERS if G in x]
        e.append(x["SEC"])
        dp.append(x["SEC"] - np.mean(others))
        da.append(x["SEC"] - x["ACC"])
    return {"E_SEC": e, "D_PWR": dp, "D_ACC": da}


# ----------------------------------------------------------------- noise baseline

def noise_baseline(season, games, teams, grp, last_w, rng):
    n = len(teams)
    idx = {t: i for i, t in enumerate(teams)}
    hi = games.home.map(idx).to_numpy()
    ai = games.away.map(idx).to_numpy()
    home = np.where(games.neutral_site.to_numpy(), 0.0, 1.0)
    final = games[games.week <= last_w]
    fh, fa = final.home.map(idx).to_numpy(), final.away.map(idx).to_numpy()
    fhome = np.where(final.neutral_site.to_numpy(), 0.0, 1.0)
    r_star, h_star = performance_fast(fh, fa, fhome, final.margin.to_numpy(), n)
    implied = r_star[hi] - r_star[ai] + h_star * home
    keep = games.week.to_numpy() <= last_w
    s = float(np.std(games.margin.to_numpy()[keep] - implied[keep]))
    fbs = teams[:-1]
    true_key = pd.Series(-r_star[:-1], index=fbs)
    true_slot, _ = shares(true_key)
    gser = grp[fbs]
    weeks = list(range(FIRST_WEEK, last_w + 1))
    acc = {G: [] for G in GROUPS}
    for _ in range(N_SIM):
        sim = games.copy()
        sim["margin"] = implied + rng.normal(0.0, s, len(games))
        for w in weeks:
            played = sim[sim.week <= w]
            opp, ven, mask, wins, phi, pai = schedule_arrays(played, teams, list(range(n - 1)))
            ph = np.where(played.neutral_site.to_numpy(), 0.0, 1.0)
            r, h = performance_fast(phi, pai, ph, played.margin.to_numpy(), n)
            b = bench_value(r[:-1], "top25")
            p = sor_probs(opp, ven, wins, mask, r, h, b, SIGMA)
            sim_slot, _ = shares(pd.Series(p, index=fbs))
            for G in GROUPS:
                sel = gser == G
                if sel.any():
                    acc[G].append(float(true_slot[sel].sum() - sim_slot[sel].sum()))
    return {G: float(np.mean(v)) for G, v in acc.items() if v}, s


# ----------------------------------------------------------------- main

def main():
    tw = pd.read_csv(TABLE)
    offsets = offsets_from_t4()
    frames, extras = {}, {}
    for season in SEASONS:
        d, games, teams, grp, last_w, n_late = run_season(season, tw, offsets)
        frames[season] = d
        extras[season] = (games, teams, grp, last_w, n_late)
        print(f"{season}: {d.week.nunique()} polls, late games moved: {n_late}")
    allw = pd.concat(frames.values(), ignore_index=True)
    names = [v[0] for v in variants()]
    for nm in names:
        allw[f"sor_rank_{nm}"] = allw.groupby(["season", "week"])[f"sor_{nm}"].rank(method="average")
    allw["colley_rank"] = allw.groupby(["season", "week"]).colley.rank(ascending=False, method="average")
    allw["perf_rank"] = allw.groupby(["season", "week"]).performance.rank(ascending=False, method="average")
    prim = f"sor_{PRIMARY[0]}|x{PRIMARY[1]}"

    hist = {s: allw[(allw.season == s)] for s in HIST}
    report = {"sigma": SIGMA, "variants": names, "primary_variant": prim}

    # Primary: E_SEC, D_PWR, D_ACC vs SOR (slots), polls 6+.
    per = {s: season_excess(hist[s], prim, True) for s in HIST}
    q = quantities(per)
    prim_stats = {k: tstats(v) for k, v in q.items()}
    for k in prim_stats:
        prim_stats[k]["bootstrap_seasons_ci95"] = boot_seasons(q[k])
    report["primary"] = prim_stats
    report["primary_by_group"] = {G: tstats([per[s][G] for s in HIST if G in per[s]])
                                  for G in GROUPS if all(G in per[s] for s in HIST) or G == "Pac-12"}
    report["label_part1"] = label_part1(prim_stats["E_SEC"], prim_stats["D_PWR"])
    report["label_part2"] = label_part2(prim_stats["D_ACC"])

    # Robustness gate.
    gate = {}
    for nm in names:
        p = {s: season_excess(hist[s], f"sor_{nm}", True) for s in HIST}
        gate[f"SOR {nm}"] = {k: float(np.mean(v)) for k, v in quantities(p).items()}
    p = {s: season_excess(hist[s], prim, True, use="pts") for s in HIST}
    gate["rank points"] = {k: float(np.mean(v)) for k, v in quantities(p).items()}
    p = {s: season_excess(hist[s], "colley", False) for s in HIST}
    gate["Colley top 25"] = {k: float(np.mean(v)) for k, v in quantities(p).items()}
    fore = {}
    for s in HIST:
        dd = hist[s]
        final = dd[dd.week == dd.week.max()]
        fore[s] = season_excess(dd, prim, True, foresight=final)
    qf = quantities(fore)
    gate["end-of-season SOR (foresight)"] = {k: float(np.mean(v)) for k, v in qf.items()}
    report["foresight"] = {k: tstats(v) for k, v in qf.items()}
    robust = {}
    for k in ("E_SEC", "D_PWR", "D_ACC"):
        m0 = prim_stats[k]["mean"]
        vals = [g[k] for g in gate.values()]
        robust[k] = {"same_sign_everywhere": bool(all(np.sign(v) == np.sign(m0) for v in vals)),
                     "within_band_everywhere": bool(all(abs(v) <= BAND for v in vals)),
                     "min": float(min(vals)), "max": float(max(vals))}
    report["robustness_gate"] = {"by_check": gate, "summary": robust}

    # Descriptive: performance top 25 (not blind; see log).
    p = {s: season_excess(hist[s], "performance", False) for s in HIST}
    report["performance_top25_descriptive"] = {k: tstats(v) for k, v in quantities(p).items()}

    # Headline levels.
    lev = {G: {"ap25": [], "sor25": [], "sor10": [], "ap25_per_member": [], "sor25_per_member": [],
               "ap10_held_in_sor10": []} for G in GROUPS}
    sec_minus_acc_sor25 = []
    for s in HIST:
        dd = hist[s]
        acc_s = {G: {k: [] for k in lev[G]} for G in GROUPS}
        diff = []
        for w, d in dd.groupby("week"):
            key = d.set_index("team")[prim]
            s25, _ = shares(key)
            s10, _ = shares(key, 10)
            a25, _ = shares(d.set_index("team").ap_rank)
            a10, _ = shares(d.set_index("team").ap_rank, 10)
            g = d.set_index("team").group
            c = {}
            for G in GROUPS:
                sel = g == G
                if not sel.any():
                    continue
                mem = sel.sum()
                c[G] = s25[sel].sum()
                acc_s[G]["ap25"].append(a25[sel].sum())
                acc_s[G]["sor25"].append(s25[sel].sum())
                acc_s[G]["sor10"].append(s10[sel].sum())
                acc_s[G]["ap25_per_member"].append(a25[sel].sum() / mem)
                acc_s[G]["sor25_per_member"].append(s25[sel].sum() / mem)
                if a10[sel].sum() > 0:
                    acc_s[G]["ap10_held_in_sor10"].append(
                        float(np.minimum(a10[sel], s10[sel]).sum() / a10[sel].sum()))
            diff.append(c["SEC"] - c["ACC"])
        sec_minus_acc_sor25.append(np.mean(diff))
        for G in GROUPS:
            for k in lev[G]:
                if acc_s[G][k]:
                    lev[G][k].append(float(np.mean(acc_s[G][k])))
    report["headline_levels"] = {G: {k: (float(np.mean(v)) if v else None) for k, v in lev[G].items()}
                                 for G in GROUPS}
    report["sec_minus_acc_sor_top25"] = tstats(sec_minus_acc_sor25)

    # Week bands (descriptive).
    bands = {"polls 6-8": (5, 7), "polls 9-11": (8, 10), "polls 12+": (11, 99)}
    rb = {}
    for bname, (lo, hi_) in bands.items():
        pb = {s: season_excess(hist[s][hist[s].week.between(lo, hi_)], prim, True) for s in HIST}
        rb[bname] = {k: float(np.mean(v)) for k, v in quantities(pb).items()}
    pe = {s: season_excess(hist[s][hist[s].week == hist[s].week.max()], prim, True) for s in HIST}
    rb["end of regular season"] = {k: float(np.mean(v)) for k, v in quantities(pe).items()}
    report["week_bands"] = rb

    # Secondary team-level gap (descriptive; whole-season resampling).
    h_all = pd.concat(hist.values())
    u = h_all[(h_all.ap_rank <= 25) | (h_all[f"sor_rank_{prim[4:]}"] <= 25)].copy()
    u["gap"] = u[f"sor_rank_{prim[4:]}"].clip(upper=26) - u.ap_rank.fillna(26)
    sec_gap = {}
    rng = np.random.default_rng(0)
    for G in GROUPS:
        ug = u[u.group == G]
        if ug.empty:
            continue
        per_s = ug.groupby("season").gap.agg(["sum", "count"]).reindex(HIST).fillna(0)
        idx = rng.integers(0, len(HIST), size=(N_BOOT, len(HIST)))
        sm, ct = per_s["sum"].to_numpy(), per_s["count"].to_numpy()
        b = sm[idx].sum(1) / np.maximum(ct[idx].sum(1), 1)
        sec_gap[G] = {"mean_gap": float(ug.gap.mean()), "team_weeks": int(len(ug)),
                      "ci95_season_bootstrap": [float(x) for x in np.percentile(b, [2.5, 97.5])]}
    report["team_level_gap_descriptive"] = sec_gap

    # Noise baseline (descriptive).
    base, obs_minus = {}, {G: [] for G in GROUPS}
    for s in HIST:
        games, teams, grp, last_w, _ = extras[s]
        b, sd = noise_baseline(s, games, teams, grp, last_w, np.random.default_rng([0, s]))
        base[s] = {"baseline": b, "noise_sd": sd}
        for G in b:
            if G in per[s]:
                obs_minus[G].append(per[s][G] - b[G])
        print(f"noise baseline {s} done (sd {sd:.1f})")
    q_obs_minus = quantities({s: {G: per[s][G] - base[s]["baseline"][G] for G in per[s]} for s in HIST})
    report["noise_baseline"] = {
        "per_season": base,
        "observed_minus_baseline": {k: tstats(v) for k, v in q_obs_minus.items()},
        "by_group_observed_minus_baseline": {G: float(np.mean(v)) for G, v in obs_minus.items() if v},
    }

    # 2026 (descriptive).
    d26 = allw[allw.season == 2026].copy()
    w26 = int(d26.week.max())
    rng_cols = [f"sor_rank_{nm}" for nm in names]
    d26["sor_rank_min"] = d26[rng_cols].min(axis=1)
    d26["sor_rank_max"] = d26[rng_cols].max(axis=1)
    pr = f"sor_rank_{prim[4:]}"
    show = d26[(d26.ap_rank <= 25) | (d26[pr] <= 25) | (d26.colley_rank <= 25) | (d26.perf_rank <= 25)].copy()
    show["record"] = show.wins.astype(str) + "-" + show.losses.astype(str)
    show["sor_rank"] = show[pr]
    show["sor_minus_ap"] = show.sor_rank.clip(upper=26) - show.ap_rank.fillna(26)
    show = show.sort_values("sor_rank")
    show[["team", "group", "record", "ap_rank", "sor_rank", "sor_rank_min", "sor_rank_max",
          "colley_rank", "perf_rank", "sor_minus_ap"]].to_csv(OUT_2026, index=False)
    c26 = season_excess(d26, prim, True)
    hist_poll9 = []
    for s in HIST:
        dd = hist[s][hist[s].week == w26]
        if not dd.empty:
            hist_poll9.append(season_excess(dd, prim, True))
    def rank_of(val, xs):
        return int(1 + sum(x > val for x in xs))
    report["2026"] = {
        "week": w26, "ap_poll": w26 + 1,
        "E_SEC": c26["SEC"], "E_ACC": c26["ACC"], "D_ACC": c26["SEC"] - c26["ACC"],
        "rank_among_historical_same_poll (1 = highest, out of n+1)": {
            "E_SEC": rank_of(c26["SEC"], [h["SEC"] for h in hist_poll9]),
            "E_ACC": rank_of(c26["ACC"], [h["ACC"] for h in hist_poll9]),
            "D_ACC": rank_of(c26["SEC"] - c26["ACC"], [h["SEC"] - h["ACC"] for h in hist_poll9]),
            "n_historical": len(hist_poll9)},
        "counts": poll_counts(d26, prim, True),
    }

    pub = allw[["season", "week", "team", "group", "wins", "losses", "performance", "colley",
                prim, f"sor_rank_{prim[4:]}", "colley_rank", "perf_rank"]].rename(
        columns={prim: "sor_probability", f"sor_rank_{prim[4:]}": "sor_rank"})
    pub.round(6).to_csv(WEEKLY, index=False)
    OUT.write_text(json.dumps(report, indent=2) + "\n")

    e = prim_stats
    print(f"PART 1: {report['label_part1']}")
    print(f"PART 2: {report['label_part2']}")
    for k in ("E_SEC", "D_PWR", "D_ACC"):
        x = e[k]
        print(f"  {k}: {x['mean']:+.2f} (95% t {x['ci95_t'][0]:+.2f}, {x['ci95_t'][1]:+.2f}; 90% "
              f"{x['ci90_t'][0]:+.2f}, {x['ci90_t'][1]:+.2f}) positive {x['seasons_positive']}/11, "
              f"sign-flip p {x['sign_flip_p']:.3f}")
    print("robustness:", json.dumps(robust))


if __name__ == "__main__":
    main()
