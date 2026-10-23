# Does Starting Ranked Explain SEC Strength?

A study of week-to-week AP poll movement, testing whether SEC teams look tougher mainly because they start the season ranked. Pre-registered plan with logged deviations; the main findings come from follow-up tests added during the analysis.

- **Plan:** [`METHODOLOGY.md`](METHODOLOGY.md), committed before any data was pulled.
- **Changes to the plan:** [`DEVIATIONS.md`](DEVIATIONS.md), each dated and committed before use, with what had been seen at the time.

## About this study

- Kyle Bowlsbey is a Miami (ACC) fan, and the claim tested here is one he believed going in.
- The code and report were written with Claude Code under his direction.
- Several analysis choices changed during the work after earlier results had been seen. Each is logged in `DEVIATIONS.md` and listed in the report (§6).
- An outside review of the first version found that the schedule result (H5) mixed a real effect with a measurement artifact. The findings below reflect the corrected analysis; the original numbers are kept in the report.

## Status

| Step | State |
| --- | --- |
| Methodology committed | Done |
| Raw data frozen with checksums (`data/MANIFEST.json`) | Done |
| Data checks and deviations logged | Done |
| Team-week feature table and leakage tests | Done |
| Models trained on 2014–2023 (no 2020), selection rule frozen | Done |
| Season replay checked on training seasons (`results/replay_training.json`) | Done |
| Revised model (per-voter points, season record) logged and re-checked on training seasons | Done |
| Holdout (2024–2025) scored once (`results/holdout.json`) | Done: primary model passes |
| Hypothesis tests (`results/hypothesis.json`, `results/bias_tests.json`) | Done |
| Season-only strength rating (`results/season_rating_validation.json`) | Done |
| H5 sensitivity after outside review (`results/h5_sensitivity.json`) | Done |
| Report (`REPORT.md`) | Done; revised after outside review |
| 2026 counterfactual (`results/counterfactual_2026*.json`) | Run; every model fails a plausibility check (`results/base_rates_poll8.json`) |

## Findings

The full write-up, with 25 figures covering every step from data to counterfactual, is in [`REPORT.md`](REPORT.md). Figures are in [`results/figures/`](results/figures/). In brief, on 2014–2025 AP polls. Registered tests are marked as such; the rest were added during the analysis.

1. **Preseason standing persists for everyone** (registered, as defined in deviation 9). About half of a team's preseason standing still shows up after week five at the same record, margin and strength. It persists no more for the SEC than for the ACC.
2. **Voters do not score SEC games more generously** (added). For the same result against the same quality of opponent, SEC and ACC teams move alike after wins and after losses.
3. **SEC opponents are ranked higher on game day than their season results justify** (added). On a matched top-25 scale, SEC schedules look about 6 places tougher (of ~130) by opponents' game-day rank than by their final results (95% CI +2.9 to +8.9). The ACC shows no such effect, and the SEC-minus-ACC gap (+3.5, 95% CI −0.8 to +8.0) is not statistically clear. The first version reported a 13.7-place gap and said ACC schedules were undersold; most of that was a measurement artifact.
4. **Net effect:** SEC teams rank about one place above their current-season results (95% CI +0.3 to +1.9; added), similar to the Big 12. The ACC is not distinguishable from zero, and neither is the SEC-minus-ACC difference (+0.76, 95% CI −0.43 to +1.93).
5. **The registered tests on their own point slightly the other way.** The linear conference test (H1) favors the SEC only in a model that fits worse than predicting no change, and against Elo (H2) the poll rates ACC teams above Elo and SEC teams in line with it. The season-only yardstick replaced Elo after those results were seen, because preseason Elo carries two-thirds of last season.
6. **SEC preseason rankings are not unjustified** (added last, T1). SEC preseason-ranked teams finish almost exactly where their preseason rank predicts (+0.09 places, 95% CI −1.63 to +1.89); ACC preseason picks hold up no better.
7. **The SEC's schedule boost is season-long, shows no preseason link, and is bigger than the ACC's** (added last, T2). Per game, SEC opponents look 0.6 to 1.2 places better on game day than their seasons end up, in every part of the season; the ACC's are about even. Measured per game, the SEC-minus-ACC difference is clear in every part of the season (the coarser schedule-rank version in point 3 is not).
8. **It is not an in-season voter loop either** (added last, T3). SEC teams that lose to ranked SEC rivals end up ranked about where their seasons finish (+0.44 places, 95% CI −0.67 to +1.43), no differently from ACC teams. The SEC plays four times as many of these games, but each is judged like anyone else's. Every qualifying game is in [`results/t3_loop_games.csv`](results/t3_loop_games.csv).
9. **The results rating does not overrate the SEC** (added last, T4). Against outsiders, including bowls the rating never saw, SEC teams beat its predictions by 3.4 points a game (95% CI +1.7 to +5.0), and match them against power-conference opponents. So "SEC schedules are tougher by results" is not a quirk of the rating. Raw head-to-head, the SEC went 58–46 against the ACC over 2014–2025.
10. **The SEC/ACC preseason swap could not be answered reliably.** Every model is stickier than real voters and fails a plausibility check that the real 2026 poll passes.

## 2026 so far: who is over- and underrated (exploratory)

After week 7, comparing each team's AP rank with its rank by this season's results, and checking that voters have also moved it more (or less) than results usually earn. Not a hypothesis test; seven weeks of games make ratings noisy.

- **Overrated:** SMU (AP #23, 39th by results), Iowa (#15, 28th), Utah (#10, 17th), Kentucky (#12, 18th), Georgia (#5, 10th), Missouri (#22, 27th).
- **Underrated:** James Madison (unranked at 7-0, 13th by results), LSU (#18, 7th), Oregon (unranked, 21st).
- Seven of the nine SEC teams on the board have schedules that look tougher by opponents' AP rank than by opponents' 2026 results.

Chart: [`results/figures/fig22_2026_over_under.png`](results/figures/fig22_2026_over_under.png). Full table: [`results/rankings_2026.csv`](results/rankings_2026.csv).

## Reproduce

```bash
pip install -r requirements.txt
export CFBD_API_KEY=...    # free key: https://collegefootballdata.com/key
python run_all.py          # downloads and verifies the raw data, then rebuilds everything
```

Raw data is not committed: CollegeFootballData.com's terms do not allow publishing stored raw API responses. `src/fetch_data.py` (the first step of `run_all.py`) downloads every raw file, schedules from the pinned cfbfastR-data commit and polls from the CFBD API, and fails unless each matches the checksum in `data/MANIFEST.json`. Once the files are present, the rest of the run is offline.

Data provided by [CollegeFootballData.com](https://collegefootballdata.com) and [sportsdataverse/cfbfastR-data](https://github.com/sportsdataverse/cfbfastR-data).

## Exploratory: team bias finder

`src/team_bias.py` compares each team's actual poll movement with the model's prediction, using out-of-season predictions on the training seasons only. It was not part of the registered plan.

```bash
python src/team_bias.py                 # leaderboard and conference summary (revised model)
python src/team_bias.py --team Miami    # one team, week by week
```

Results are written to `results/team_bias_*.csv` and `results/conference_bias_*.csv`.
