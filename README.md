# Does Starting Ranked Explain SEC Strength?

A pre-registered study of week-to-week AP poll movement, testing whether SEC teams look tougher mainly because they start the season ranked.

- **Plan:** [`METHODOLOGY.md`](METHODOLOGY.md), committed before any data was pulled.
- **Changes to the plan:** [`DEVIATIONS.md`](DEVIATIONS.md), each dated and committed before use.

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
| Report (`REPORT.md`) | Done |
| 2026 counterfactual (`results/counterfactual_2026*.json`) | Run; every model fails a plausibility check (`results/base_rates_poll8.json`) |

## Findings

The full write-up, with 20 figures covering every step from data to counterfactual, is in [`REPORT.md`](REPORT.md). Figures are in [`results/figures/`](results/figures/). In brief, on 2014–2025 AP polls:

1. **Preseason standing persists for everyone.** About half of a team's preseason standing still shows up after week five at the same record, margin and strength. It persists no more for the SEC than for the ACC.
2. **Voters do not score SEC games more generously.** For the same result against the same quality of opponent, SEC and ACC teams move alike after wins and after losses.
3. **The poll inflates SEC schedule strength.** By opponents' poll standing, SEC schedules look about 7 places tougher (of ~130) than opponents' results justify, and ACC schedules about 7 places easier. The SEC-minus-ACC gap is 13.7 places (95% CI 9.1–17.9).
4. **Net effect:** SEC teams rank about one place above their current-season results (95% CI +0.3 to +1.9), similar to the Big 12. The ACC is not distinguishable from zero.
5. **The SEC/ACC preseason swap could not be answered reliably.** Every model is stickier than real voters and fails a plausibility check that the real 2026 poll passes.

## Reproduce

```bash
pip install -r requirements.txt
python run_all.py          # rebuilds everything from the frozen files in data/raw
```

`src/pull_data.py` is the only script that touches the network. It needs a free [CollegeFootballData.com](https://collegefootballdata.com) key in `CFBD_API_KEY`.

## Exploratory: team bias finder

`src/team_bias.py` compares each team's actual poll movement with the model's prediction, using out-of-season predictions on the training seasons only. It was not part of the registered plan.

```bash
python src/team_bias.py                 # leaderboard and conference summary (revised model)
python src/team_bias.py --team Miami    # one team, week by week
```

Results are written to `results/team_bias_*.csv` and `results/conference_bias_*.csv`.
