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
| Holdout (2024–2025) scored once | Not yet |
| Hypothesis test | Not yet |
| 2026 counterfactual | Not yet |

## Reproduce

```bash
pip install -r requirements.txt
python run_all.py          # rebuilds everything from the frozen files in data/raw
```

`src/pull_data.py` is the only script that touches the network. It needs a free [CollegeFootballData.com](https://collegefootballdata.com) key in `CFBD_API_KEY`.

## Exploratory: team bias finder

`src/team_bias.py` compares each team's actual poll movement with the model's prediction, using out-of-season predictions on the training seasons only. It was not part of the registered plan.

```bash
python src/team_bias.py                 # leaderboard and conference summary
python src/team_bias.py --team Miami    # one team, week by week
```

Results are written to `results/team_bias_*.csv` and `results/conference_bias_*.csv`.
