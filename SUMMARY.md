# Is the SEC overrated, or just good?

**One-page summary of this study.** Every number below comes from a file in [`results/`](results/), collected with its source in [`results/post_numbers.json`](results/post_numbers.json). Everything rebuilds with `python run_all.py`. The full write-up is [`REPORT.md`](REPORT.md).

## The question

Kyle Bowlsbey, a Miami fan, went in believing two things:

1. **"Miami has played nobody" is false.** Judged only on this season, Miami's record is strong.
2. **SEC schedules look hard because SEC teams start the season ranked.** So many SEC teams are ranked that they "swap seats": a loss is a good loss to a ranked team, a win is a tough win over one, and the cycle keeps going. Put Big Ten or ACC teams in their place and they would look just as strong.

## How it was tested

- **Seasons:** AP polls for 2014–2025, leaving out 2020.
- **Yardstick:** strength of record, built only from that season's scores and schedules. It uses no polls, no preseason information and no team names. It asks how likely a typical top-25 team would be to post this record against this schedule.
- **Procedure:** the plan was committed before any data was pulled ([`METHODOLOGY.md`](METHODOLOGY.md)). Every change was logged before use, with what had been seen at the time ([`DEVIATIONS.md`](DEVIATIONS.md)). An independent audit checked the code and the wording of the results, with skeptics asked to refute each finding.
- **Caveat:** the tests used for this summary were added during the analysis, after earlier results had been seen. Each is logged.

## Hypothesis 1: Miami "played nobody". **Not supported by results.**

After week 8 of 2026 ([`results/sor_2026.csv`](results/sor_2026.csv), [`fig28`](results/figures/fig28_2026_sor.png)):

- Miami is 7–0 and **#1 by strength of record**. It ranks between #1 and #4 across all 11 settings tested. It is #2 by wins and losses alone (Colley) and #2 by scoring margin.
- **What is true:** none of Miami's opponents was in the AP top 25 on game day. Counted that way, its schedule ranks 94th of 138.
- **What is not:** counted by how those opponents have actually played in 2026, the schedule ranks **56th of 138**. That is the middle of the pack, not "nobody".
- **Example:** Miami won 33–20 at Wake Forest in week 3. Wake Forest was unranked then. It is now 6–1, AP #14 and #9 by strength of record, and its only loss is to Miami.

One season and eight weeks of games: this part is descriptive, not a test.

## Hypothesis 2: rankings make SEC schedules look hard. **Partly supported.**

**What holds up (supports Kyle):**

- **Early polls list more SEC teams than finish top 25 on results.** In AP polls 1–5, the AP top 25 holds **1.65 more SEC teams per poll** than the end-of-season strength-of-record top 25 (95% CI +0.51 to +2.80; 10 of 11 seasons). That is the most of any conference, and it keeps its sign in every robustness check ([`results/t6_early.json`](results/t6_early.json), [`fig27`](results/figures/fig27_excess_by_stage.png)).
- **Game-day rankings flatter SEC schedules.** Ranked by opponents' AP rank on game day, SEC schedules look about **5.7 places tougher** (of ~130) than they do ranked by those opponents' final results (95% CI +2.9 to +8.9). Using the final poll instead, the gap is +1.1 (CI −0.4 to +2.4) ([`results/h5_sensitivity.json`](results/h5_sensitivity.json)).
  - Per game, SEC opponents look 0.6 to 1.2 rank points better on game day than their seasons end up. ACC opponents look about 0.1 better ([`results/preseason_tests.json`](results/preseason_tests.json)).
- **The power conferences' extra AP spots come mostly at the expense of Group of 5 teams.** From poll 6 on, the AP lists 3.3 Group of 5 and other teams per poll; strength of record has 4.8 (descriptive; [`fig26`](results/figures/fig26_sor_levels.png)).
- **SEC teams sit about one poll place above their results** (+1.1 places, 95% CI +0.3 to +1.9) ([`results/hypothesis.json`](results/hypothesis.json)). The Big 12 is similar (+1.2), and the SEC-minus-ACC difference is not clear (+0.76, CI −0.43 to +1.93).

**What does not hold up:**

- **The SEC's strength is not a ranking artifact.** With no rankings used at all, the SEC still has the most teams in the strength-of-record top 25:
  - **SEC 5.5 per poll, Big Ten 4.7, ACC 3.2.** SEC minus ACC: +2.27, 95% CI +1.23 to +3.31 ([`results/t5_sor.json`](results/t5_sor.json), [`fig26`](results/figures/fig26_sor_levels.png)).
  - In 2026 to date, 8 of the strength-of-record top 25 are SEC teams.
- **Results against outsiders back it up.** Against other conferences, including bowl games the rating never saw, SEC teams beat the results rating's predictions by **3.4 points a game** (95% CI +1.7 to +5.0), and match its predictions against power-conference opponents (−0.2). Head-to-head, the SEC went 58–46 against the ACC ([`results/t4_referee.json`](results/t4_referee.json)).
- **Ranked SEC teams fall out at the usual rate.** In polls 1–5 the SEC holds 7.2 top-25 spots. At the rates seen for every team at those AP ranks, 2.7 of them would be expected to miss the final top 25, and 2.8 do: **+0.07 beyond expected** (95% CI −0.65 to +0.78; [`fig29`](results/figures/fig29_early_decomposition.png)). The early surplus comes from the SEC having the most ranked teams, not from each SEC team being more overrated.
- **No sign of the "swap seats" loop.** SEC teams that lose to ranked SEC rivals end up ranked about where their seasons finish: +0.44 places (95% CI −0.67 to +1.43), no differently from ACC teams (+0.96) ([`results/t3_loop.json`](results/t3_loop.json)).
- **The gap fades.** Measured against the end-of-season record, the SEC's extra AP spots fall from +1.65 per poll in polls 1–5 to +0.45 by the final regular-season poll, which is not statistically clear.
- **The season-long surplus is fragile.** From poll 6 on, the AP lists 0.68 more SEC teams per poll than strength of record does. Calibrate the rating to each conference's results against outsiders, and that falls to +0.08. The pre-set robustness rule therefore marks the season-long result **not robust**.

## Bottom line

- **Miami's #1 ranking is backed by its results.**
- **"Ranked wins" and game-day schedule ranks oversell SEC schedules, most of all early in the season.** A September "ranked" opponent is often not a top-25 team by season's end. That is true for every conference, and the SEC has the most such opponents. Use results-based measures instead.
- **By results alone, the SEC is still the strongest conference.** Its high rankings are mostly earned. What rankings add is about one poll place, and the Big 12 gets about as much.

## What this does not show

- **Not proof of intent.** Early polls reflect what voters knew then. "Not justified by how the season turned out" is hindsight.
- **One yardstick.** Strength of record is one model of a résumé. It was checked across 9 settings, two calibrations, a rank-weighted count and a wins-and-losses ranking, and the checks that fail are reported above.
- **2026 is descriptive.** Eight weeks of games; no test.
- **Added late.** Several tests were added after earlier results were seen. They are logged in `DEVIATIONS.md` and listed in the report.

## Check it yourself

- **Every number, with its source:** [`results/post_numbers.json`](results/post_numbers.json)
- **Test definitions, logged before running:** `DEVIATIONS.md`, entries T5 and T6, and the post-audit corrections of 2026-10-31.
- **Week-by-week strength of record for every team, 2014–2026:** [`results/sor_weekly.csv`](results/sor_weekly.csv)
- **Rebuild everything:** `pip install -r requirements.txt`, set a free `CFBD_API_KEY`, then `python run_all.py`. The raw data is checked against `data/MANIFEST.json`.

Data: [CollegeFootballData.com](https://collegefootballdata.com) and [sportsdataverse/cfbfastR-data](https://github.com/sportsdataverse/cfbfastR-data). Code and write-up by Claude Code under Kyle's direction.
