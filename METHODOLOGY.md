# Does Starting Ranked Explain SEC Strength? — Pre-Registered Methodology

2026-10-23 · Kyle Bowlsbey

Source of record: https://claude.ai/artifact/Cw43qEWovg8SoVPR4KJzsi (copied verbatim at commit time).

## Question and hypothesis

This study tests whether SEC teams look tougher mainly because they start the season ranked. Wins over ranked opponents earn more poll credit, so a conference full of preseason-ranked teams could inflate itself.

- **Claim under test:** preseason rank, not on-field strength, drives much of the SEC's perceived schedule strength.
- **Supports the claim:** swapping SEC and ACC preseason slots moves ACC teams up substantially by late season, and SEC poll standing sits above what an independent strength rating (Elo) predicts.
- **Refutes the claim:** swapped ACC teams fall back toward their actual positions, and SEC poll standing matches Elo.

This methodology is written and dated before any model is trained or any result is seen.

## Data sources

Two public sources, frozen once and never re-pulled mid-analysis.

| Data | Source | Seasons | Use |
| --- | --- | --- | --- |
| Game results, conferences, pregame Elo | [sportsdataverse/cfbfastR-data](https://github.com/sportsdataverse/cfbfastR-data) | 2014–2026 | Scores, opponents, venue, independent strength rating |
| Weekly AP Top 25 with voting points | [CollegeFootballData.com API](https://collegefootballdata.com) | 2014–2026 | Poll points and rank each week (teams receiving votes, if the source provides them) |

- **Freezing:** raw files are saved as pulled, with the pull date, source URL, and a SHA-256 checksum for each file.
- **Scope:** FBS regular-season games only. 2020 is excluded because COVID scheduling and opt-outs broke normal poll behavior.
- **Conferences:** each team is tagged with its conference in that season, so realignment (Texas and Oklahoma to the SEC, SMU, Cal and Stanford to the ACC) is handled correctly.

## Target and features

The model predicts each team's change in AP poll points from one week's poll to the next. Teams with no votes count as 0 points, so movement into and out of the poll is captured.

Every input is something voters knew before casting that ballot:

| Feature | Definition |
| --- | --- |
| Prior poll points | Team's AP points in the previous poll |
| Result | Win, loss, or bye that week |
| Points scored / allowed | Final score of that week's game |
| Margin | Points scored minus points allowed |
| Opponent poll points | Opponent's AP points in the previous poll |
| Venue | Home, away, or neutral |
| Losses above | Number of teams ranked above this team that lost that week |
| Week | Week of season, since voters move teams less late in the year |
| Conference | SEC, ACC, Big Ten, Big 12, or other (used only in the hypothesis test) |

Elo is never a model input. It is held back as the independent check in the hypothesis test.

## Model and validation

The model trains on 2014–2023 and is scored once on 2024–2025, seasons it never sees during training. Nothing is tuned against the holdout.

1. **Naive baseline:** predict no change for every team. This is the floor any model must beat.
2. **Primary model:** linear regression on the features above. Every coefficient is readable, so anyone can check what voters reward.
3. **Challenger:** gradient-boosted trees, used only if they beat the linear model on the holdout by more than 10% in mean absolute error.

**Pass criteria:** the chosen model beats the naive baseline on holdout mean absolute error, and its predicted end-of-season top 25 matches the real 2024 and 2025 final polls with a rank correlation of at least 0.7. If it fails, the counterfactual is not run and that result is reported as is.

## Hypothesis test

Two checks run on 2014–2025, each with a 95% confidence interval from a bootstrap that resamples whole team-seasons.

1. **Conference effect on movement.** Add conference flags to the linear model. The SEC-minus-ACC coefficient shows whether, for the same result, margin and opponent, SEC teams gain more poll points. An interval that includes zero means no evidence of a conference-specific voter effect.
2. **Poll versus strength.** For each team-week, compare poll rank to Elo rank. If SEC teams sit consistently higher in the poll than their Elo justifies, and ACC teams lower, that supports the claim. If both conferences track Elo equally, it does not.

The second check matters most. SEC teams may start ranked because they are strong, and Elo is the closest available measure of strength that does not come from voters.

One known weakness: Elo carries over part of each team's prior season, so it can share some of the polls' preseason inertia. That limit will be stated alongside the result.

## 2026 counterfactual

The 2026 preseason poll is rewritten with SEC and ACC slots swapped, then the real 2026 results are replayed through the trained model.

1. **Pair the teams.** Order SEC teams by preseason poll points, then ACC teams the same way. The top SEC team swaps points with the top ACC team, second with second, and so on. Teams left without a partner keep their real points.
2. **Replay week by week.** Each week, every team plays its real game with its real score. Opponent poll points come from the simulated poll, not the real one, so the swap ripples through schedule strength.
3. **Compare.** Report each paired team's simulated versus real poll position for every completed 2026 week, and the conference totals of top-25 slots.
4. **Sanity run.** Replay 2026 once with no swap. Its drift from the real poll is the model's error bar, and any swap effect smaller than that drift is reported as noise.

## Commitments and limitations

Results get published whichever way they point, including any that cut against the claim.

- **Public record:** code, frozen data with checksums, and this methodology go in a public GitHub repo. The commit history shows this plan existed before any result.
- **Deviations logged:** any change to this plan after data is pulled gets a dated note explaining why. Nothing changes silently.
- **Reproducible:** one command rebuilds every number from the frozen files.

What this study cannot show:

- It models how voters react, not which teams are actually better.
- The counterfactual assumes 2026 games end with the same scores. In reality, a higher-ranked team might play or be scheduled differently.
- Poll points are partly zero-sum. A per-team model captures that only through the losses-above feature, so simulated totals may not add up exactly to a real ballot.
- Elo is the only independent strength measure used, and it has its own preseason assumptions.
