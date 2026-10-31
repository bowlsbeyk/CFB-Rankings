# Deviations from METHODOLOGY.md

Each entry is dated and committed before the change it describes is used.

## 2026-10-23 — CFBD polls stop at #25 (no "others receiving votes")

**What the methodology says:** teams with no votes count as 0 points; the target is the week-to-week change in AP points.

**What the data shows:** every CFBD AP poll from 2014 through 2026 lists ranks 1–25 only (26 entries when two teams tie at #25). Teams that received votes but finished outside the top 25 do not appear, so their points are unknown, not zero. Checked by `src/verify_data.py`.

**Effect:** a team moving between #26-ish and the top 25 looks like a jump from or to 0 points, which overstates movement at the bottom edge of the poll.

**Decision (Kyle, 2026-10-23):** run both, see the next entry.

Other open questions, resolved with no deviation:
- Name matching: every AP-ranked school in every season matches a team in the cfbfastR-data schedules.
- Preseason poll: CFBD regular-season week 1 is the preseason poll in every season (e.g. 2025 week 1 has Texas #1; after Texas lost in week 1, week 2 has Ohio State #1).

## 2026-10-23 — Unranked points: primary 0 rule plus a censored-floor sensitivity run

Kyle chose to run both treatments.

- **Primary (as registered):** every FBS team not in the AP top 25 has 0 points.
- **Sensitivity (added):** every FBS team not in the AP top 25 has half the points of the lowest-ranked team in that same poll (the midpoint of the 0 to #25 range that vote-getters outside the top 25 fall in). Fixed now, before any model is fit; not tuned.

The same rule feeds every points-based quantity (target, prior poll points, opponent poll points). Every model, holdout score and hypothesis test is run under both. The primary result is the one reported first. If they disagree, both are reported.

## 2026-10-23 — Clarifications on game handling (no change to the plan's intent)

- **Week 0.** cfbfastR-data labels "week 0" games as week 1. The preseason poll comes before them and the week-2 poll after, so a few teams per season (0 to 16) play twice between those two polls. For those team-weeks the result is encoded as counts (wins, losses), scores and margin are summed, opponent poll points are summed, and venue is counted. For every other team-week this encoding is identical to the single-game one (a bye is 0 wins and 0 losses).
- **Postseason rows.** The schedule files include bowl and playoff games labeled `season_type == "postseason"`, also numbered from week 1. They are excluded: the study models regular-season polls only.
- **FBS scope.** Rows are FBS teams in that season. A regular-season game an FBS team plays against an FCS opponent counts as a game (opponent poll points 0), not a bye.

## 2026-10-23 — Exploratory addition: team bias finder (not pre-registered)

`src/team_bias.py` lists which teams the model consistently over- or under-predicts (for example, ranked teams that fall further than predicted after a loss). It uses out-of-season predictions on the 2014–2023 training seasons only. It is exploratory: it was not in the registered plan, its results are labeled as such, and nothing in it feeds the model choice, the holdout or the counterfactual.

## 2026-10-23 — Games played after the poll they would feed are dropped

The leakage test found that cfbfastR-data labels the 2019 Army–Navy game (Dec 14) as week 15. The last regular-season AP poll came out Dec 8, so that game cannot have moved it.

**Rule:** a game counts toward schedule week w only if it kicked off by Tuesday 12:00 US Eastern after week w's busiest game day. That keeps Monday-night Labor Day games and Tuesday MAC games in their week and drops anything played after the next poll. `build_features.py` prints every dropped game.

## 2026-10-23 — Replay details and the end-of-season pass test (clarification, before any holdout use)

The methodology says the replayed end-of-season top 25 must match the real final poll with Spearman ≥ 0.7. It leaves three details open. They are fixed here, from training seasons only, before 2024–2025 is touched.

- **Replay mechanics.** Start from the real preseason (week 1) AP points. Each week, every team plays its real games; prior points, opponent points and losses-above come from the simulated poll. New points = prior + predicted change, floored at 0. After each week, teams are re-ranked by simulated points and teams outside the top 25 get the unranked value (0, or half the simulated #25 under the floor rule), matching how the training data treat unranked teams.
- **Which final poll.** The replay covers the regular season only (bowls are not modeled), so the pass test uses the last regular-season AP poll. The post-bowl final poll is reported alongside as a secondary check.
- **How Spearman is computed.** Over the real final top 25: each team's real rank versus its rank in the simulated poll among all FBS teams (by simulated points; teams the replay drops from the top 25 are ranked by their last ranked points). Top-25 overlap is reported alongside.
- **Reference.** The same numbers for "the preseason poll never changes" are reported, so readers can see how much the model adds.

## 2026-10-23 — Model revisions after the training-season replay check (before any holdout use)

**Why.** The replay check on training seasons (`results/replay_training.json`, commit b947cb2) showed the model is too attached to preseason rank. It let 73 teams climb into the final top 25 against 93 in reality, and kept 152 preseason-ranked teams ranked against 132 in reality. That would overstate any effect of starting rank, which favors the claim under test. Separately, the AP panel grew from about 58–63 voters (2014–2023) to about 66 (2025) and 69–70 (2026), so raw points are not comparable across seasons. These changes were decided by Kyle on 2026-10-23, after seeing training-season results only. Nothing from 2024–2026 has been scored.

1. **Season-to-date record as inputs.** Three features are added: wins to date, losses to date, and mean margin to date, each counting regular-season games through the current week (all played before the poll being predicted). Without them, an unranked 7-0 team and an unranked 3-4 team look the same to the model.
2. **Points per voter.** Every points quantity (target, prior points, opponent points, the floor value) is divided by that poll's number of voters, counted as the total of first-place votes. Rankings are unchanged; seasons become comparable.
3. **Stickiness check reported with the counterfactual.** On training seasons, with the final model, measure how many rank spots the replay keeps preseason-ranked teams above their real final rank (unranked counts as 26). For each paired team in the 2026 swap, a rank gain no larger than that stickiness is reported as indistinguishable from model inertia.
4. **"Elo says ranked, AP didn't" table in the hypothesis test.** Each week, list teams in the Elo top 25 (postgame Elo after that week's games) that are outside the next AP top 25, and AP-ranked teams outside the Elo top 25, counted by conference. This makes check 2 (poll versus strength) concrete. Elo stays out of the model.

**Registered model kept for the record.** The original specification (raw points, no record features) is still trained, replayed and scored on the holdout, and its results are reported next to the revised model's. The revised model is the one used for the hypothesis test and the counterfactual, subject to the same selection rule and pass criteria.

## 2026-10-23 — Stickiness yardstick and swap pairing (before the counterfactual is run)

**Yardstick (Kyle's decision).** The holdout showed more stickiness than the training seasons: under the 0 rule the replay kept preseason-ranked teams +1.72 (2024) and +2.16 (2025) rank spots above their real final rank, against +0.75 on training seasons. The yardstick is the larger of the training figure and the holdout mean, per unranked rule, so it is always the cautious one:
- 0 rule (primary): **1.94 spots** (holdout mean; training was 0.75).
- Floor rule: **0.44 spots** (training; the holdout mean was −0.40).

A paired team's swap gain (its rank with the swap versus without, both simulated) no larger than the yardstick is reported as indistinguishable from model inertia.

**Pairing.** The 2026 preseason poll ranks 9 SEC teams and 3 ACC teams, so ordering by preseason points leaves SEC teams #4–9 without a partner, and the 14 unranked ACC teams cannot be ordered by points.
- **Primary (literal reading of the methodology):** the 3 ranked ACC teams swap points with the top 3 SEC teams by points. Every other team keeps its real points.
- **Extension (logged, reported alongside):** all 9 ranked SEC slots go to ACC teams. Unranked teams in each conference are ordered by preseason Elo (pregame Elo for their first 2026 game), used only to form pairs, never as a model input.

**Model.** The chosen model from the holdout (revised spec, challenger), as fit on 2014–2023. It is not refit on 2024–2025. Both unranked rules are run; the 0 rule is primary.

## 2026-10-23 — Post-hoc plausibility check on the counterfactual (added after seeing its results)

The counterfactual was run exactly as logged (`results/counterfactual_2026.json`). Its biggest moves came from teams the swap pushed far from their record: in the 9-slot extension, 6-1 Tennessee (average margin +18.7) never re-enters the top 25 through poll 8, while 4-3 Virginia and Louisville sit near #15. To judge whether voters would do that, `src/base_rates.py` counts what real AP voters did at poll 8 in 2014–2025 for those situations. This check was not planned in advance; it was added because the results looked implausible, and it is reported as such.

## 2026-10-23 — Hypothesis test definitions (fixed before it is run)

All three checks use real 2014–2025 data (no 2020), the revised units (points per voter, 0 rule as primary, floor rule as sensitivity), and 95% intervals from 1,000 bootstrap resamples of whole team-seasons (seed 0).

1. **Conference effect (registered check 1).** The revised linear model plus SEC, ACC, Big Ten and Big 12 flags (other = reference). Reported: the SEC-minus-ACC coefficient. The registered spec is reported too.
2. **Poll versus Elo (registered check 2).** Elo rank = rank among FBS teams by Elo after week w's games (last available postgame Elo, carried forward over byes and FCS games). It is compared with AP rank in poll w+1. Team-weeks where the team is in the AP top 25 or the Elo top 25 are used, both ranks capped at 26. Gap = Elo rank − AP rank (positive = the poll rates the team above Elo). Reported: mean gap by conference and SEC minus ACC. Plus the logged table: per conference, "Elo top 25 but AP unranked" and "AP ranked but outside the Elo top 25" team-weeks.
3. **Preseason carry-over at equal record and strength (added, follows from the base-rate check).** Linear regression of points per voter in poll w+1 on preseason points per voter, wins to date, losses to date, mean margin to date, Elo after week w, and week, for polls 5 onward. The preseason coefficient is how much of a team's preseason standing still shows up later, holding record and Elo fixed. A version with preseason × SEC and preseason × ACC terms tests whether that carry-over is bigger for the SEC. Elo carries part of the prior season, so this likely understates carry-over; that limit is reported with it.

## 2026-10-23 — Elo replaced by a season-only rating as the strength yardstick (Kyle's decision)

**Why.** Elo is independent of voters but not of last season: a team's preseason Elo is 0.67 × (last season's final Elo − 1500) + 1500 (correlation 0.99, 1,306 team-seasons; game-level changes are 96% explained by scoring margin versus the Elo-implied expectation). Any head start a conference carries into a season (the very thing under test) is partly built into Elo too, so comparing the poll with Elo cannot detect it. The Elo-based results already committed (`results/hypothesis.json`) stay in the record and are reported with this limitation; they are no longer the primary yardstick.

**The season-only rating.** Rebuilt each week from that season's completed regular-season games only (same late-game cutoff as the features). Every team starts equal. All FCS opponents are pooled as one team.
1. **Results part (Colley method).** Solve C r = b with C_ii = 2 + games played, C_ij = −(games between i and j), b_i = 1 + (wins − losses)/2. Wins and losses only; opponents' and opponents' opponents' results enter through the joint solve.
2. **Performance part (margin-based).** Least squares on every game: margin (home − away, capped at ±28) = r_home − r_away + h × (not neutral), with h estimated. Each team also gets one pseudo-game with margin 0 against an average opponent, so early-season ratings are shrunk toward average and the system is always solvable.
3. **Combined rating.** Each part is standardized across FBS teams that week; the combined rating is their 50/50 average. Strength rank = rank of the combined rating among FBS teams.

These settings are fixed now and not tuned.

**Validation (reported, not used for tuning).** Ratings through week w predict the winners of week w+1 FBS-vs-FBS games, for predictions of week-6-and-later games, 2014–2025. Compared on the same games: combined rating, each part, Elo (higher pregame Elo), and the AP poll (better-ranked team; games with both teams unranked excluded from that comparison).

**Re-run with it.** Hypothesis checks 2 (poll versus strength, including the "rated top 25 but AP unranked" table) and 3 (preseason carry-over) are re-run with the season-only rating in place of Elo, from poll 6 onward (at least five weeks of games). Check 1 does not use a strength measure and is unchanged.

## 2026-10-23 — Rating-aware model, voter-bias test, schedule-inflation test, swap re-run (Kyle's decisions, before any of it is run)

**Elo stays as a comparison.** Elo (carries last season) versus the season-only rating (does not) is reported by conference: the gap measures how much prior-season head start each conference carries. Elo is still never a model input.

**New model specification "rated".** The revised specification plus two inputs from the season-only rating: the team's own combined rating after week w's games, and the mean combined rating of its opponents that week after week w's games (0 = average for a bye; pooled FCS opponents get the pooled FCS rating, standardized with the FBS mean and spread). Like every other input, both use only games played before the poll being predicted. No team names or conferences enter. Same models, settings and selection rule as before.
- **Clean test:** leave-one-season-out on 2014–2023 and the training-season replay check, same pass bar (Spearman ≥ 0.7).
- **Holdout:** 2024–2025 was already scored for the registered and revised specs and cannot be a clean test again. The rated spec's 2024–2025 numbers are reported as "holdout re-used", in a separate file; `results/holdout.json` is not changed.

**Voter-bias test (rewards and punishments).** Each 2014–2025 season is predicted by the rated model fit on all other 2014–2025 seasons. Residual (actual − predicted change, points per voter) is averaged by conference for ranked teams after a win, after a loss, and over all weeks, with 95% intervals from resampling team-seasons (1,000, seed 0). SEC minus ACC is reported for each. Positive after a win = rewarded more than results explain; positive after a loss = punished less.

**Schedule-inflation test.** For each FBS team-season, 2014–2025 and 2026 to date, two schedule-strength measures over its regular-season FBS-or-FCS games: poll-based = mean of opponents' AP points per voter in the poll before each game (0 rule); rating-based = mean of opponents' season-only rating after the last completed week. Each is ranked among FBS teams that season. Inflation = rating-based rank − poll-based rank (positive = the poll makes the schedule look tougher than results do). Reported by conference, with intervals from resampling team-seasons, plus SEC minus ACC.

**Swap re-run.** The 2026 counterfactual (swap3 primary, swap9 extension, sanity run, yardstick) is re-run with the rated model if it passes the training replay bar, into a separate file. Plausibility is checked against real voters, fixed now: in each simulated final poll, count Power-4 teams at 6-1 or better (or 5-0 and better at that point) left unranked, and teams with 3+ losses ranked. Real voters, 2014–2025 at poll 8: 0 of 95 such 6-1 teams left unranked; 1 of 816 teams with 3+ losses ranked (`results/base_rates_poll8.json`). A run that breaks these is reported as implausible.

## 2026-10-23 — H5 sensitivity: shape and timing matched (added after seeing H5 results)

**Prompted by an outside review** of the repository at commit `00df744`, after H5 (schedule inflation) had been published in `REPORT.md`. The reviewer had already run this check and seen its numbers before this entry was written. Those numbers are reproduced below and checked by the new script.

**The problem.** H5 compares two schedule-strength measures that differ in two ways at once:
- **Shape.** The poll side gives every unranked opponent 0; the rating side gives every opponent a continuous rating.
- **Timing.** The poll side uses the opponent's standing in the poll before the game; the rating side uses the opponent's final season-only rating.

"Inflation" therefore mixes a real effect (timing: opponents ranked on game day versus how they finished) with a measurement artifact (shape: good-but-unranked opponents count only on the rating side).

**Four variants** (2014–2025 team-seasons; schedule ranks among FBS teams with average ranks for ties; 1,000 team-season resamples, seed 0; positive = the poll makes a schedule look tougher):
- **A. As published:** opponents' AP points per voter in the poll before each game vs opponents' final season-only rating.
- **B. Shape matched:** both sides as top-25 rank points (26 − rank inside the top 25, else 0). Poll side: opponent's AP rank in the poll before the game. Rating side: opponent's final season-only rank. **This is the fairest test of the claim**: same shape, game-day poll versus final results.
- **C. Timing matched:** opponents' final regular-season AP points per voter vs final season-only rating.
- **D. Shape and timing matched:** final AP rank points vs final season-only rank points. Reported for completeness; it removes the game-day effect by design.

**Final regular-season poll.** Taken as the poll after each season's last schedule week (the `next_*` columns of the last transition in `team_weeks.csv`). The review's script used the `prior_*` columns of each team's last schedule week, which is one poll earlier. Both are computed: the review's version to check its table, the corrected one as the reported result.

**Review's numbers** (its final-poll lookup), SEC / ACC / SEC − ACC, rank places:
A +6.7 / −7.2 / +14.0; B +5.7 / +2.1 / +3.5 (CI −0.8, +8.0); C +1.2 / −9.7 / +10.9; D +0.2 / +0.1 / +0.1.

The original H5 numbers stay in `results/bias_tests.json` and the report as originally computed.

## 2026-10-23 — Raw data no longer committed; fetched and verified instead (redistribution terms)

**Why.** CollegeFootballData.com's Terms of Use (effective 2026-08-12, https://collegefootballdata.com/terms) allow privately storing API responses and publishing analyses built from them, but not giving third parties "stored raw API responses" or publishing API data "as a standalone dataset or bulk download" (Sections 2, 4 and 5). The repository committed the raw `/rankings` responses. It also committed schedule files from sportsdataverse/cfbfastR-data, which carries no license and holds CFBD-derived fields (Elo, excitement index). Both are removed from the repository from this commit on.

**What replaces them.** `data/MANIFEST.json` (source URLs, pull time, SHA-256 per file, upstream commit) stays. `src/fetch_data.py` re-downloads every file and fails unless each one matches its recorded checksum:
- Schedules: from cfbfastR-data at the pinned commit `09f2595e`. No key needed.
- Polls: from the CFBD API with a free key in `CFBD_API_KEY`. The 2026 regular-season response is cut back to the weeks that were frozen (1–8) before checking. The API's JSON re-serializes to identical bytes, so this reproduces the frozen file exactly. A test re-pull on 2026-10-23 of 8 of the 26 poll files matched their checksums byte for byte.

`run_all.py` runs `fetch_data.py` first. It downloads only files that are missing or fail their checksum, so a machine that already has them stays offline. No data value, result or figure changes.

**Not done: history.** Earlier commits, starting with `17c9e98`, still contain the files. Removing them would mean rewriting the repository's public history, which would also change every commit hash the audit trail cites. That decision is Kyle's.

## 2026-10-23 — Single-threaded model training for machine-independent results

**Found by the outside review** and confirmed here before this entry. A rebuild on another machine (same pinned packages) did not reproduce every committed number. Re-running here with training limited to one thread (`OMP_NUM_THREADS=1`) reproduced the review's numbers exactly. Gradient-boosted training sums in parallel, and the order of those floating-point sums depends on the thread count.

**What moves** (single-threaded vs the committed multi-threaded run): only the rated model under the floor rule, through its 2014 training fold. That is the training-season replay for rated/floor (2014 mean rank error 3.68 → 6.20; climbers 79 → 77; mean ρ 0.8804 → 0.8800; stickiness +0.42 → +0.46), its training error (third decimal), and the 2026 counterfactual yardstick for rated/floor (0.42 → 0.46). Every other difference is below 1e-15. `results/holdout.json` is identical. No number cited in `REPORT.md` changes.

**Change.** `run_all.py` forces one thread for every step, and `src/train.py` does the same when run directly. `numpy` and `scipy` are pinned in `requirements.txt`; every model and bootstrap already used a fixed seed. Committed results are regenerated single-threaded. The multi-threaded values above are recorded here and in git history.

## 2026-10-23 — Exploratory: who is over- and underrated in 2026 so far (Kyle's request)

Not a hypothesis test; a current-season description, fixed before it is run. Teams in the AP top 25 of poll 8 or in the season-only top 25 after week 7.
- **Results lens:** season-only rating rank after week 7 minus AP rank in poll 8 (positive = the AP ranks the team above its results).
- **Voter lens:** for every 2026 team-week, actual change in AP points per voter minus the change the name-blind rated model (fit on 2014–2023, 0 rule) predicts from that week's real prior poll and results, summed over weeks 1–7 and divided by 0.80 points per voter per rank place (positive = voters lifted the team more than results usually earn).
- **Schedules:** schedule rank among FBS teams by opponents' game-day AP rank points versus by opponents' current season-only rank points (the shape-matched scale of H5 variant B).
- A team is called clearly over- or underrated only when both lenses agree in sign and the results lens is at least 5 places.

Limits stated with the output: seven weeks of games make ratings noisy; the rating sees only scores, not injuries or quarterback changes.

## 2026-10-23 — Two tests of the preseason link (Kyle's request; added after all earlier results)

Added to close two gaps in the claim, after every earlier result (including the H5 sensitivity and the 2026 board) had been seen. Definitions and the reading of each result are fixed here, before either is run. Both use 2014–2025 (no 2020), the 0 rule, and 95% intervals from 1,000 resamples of team-seasons (seed 0). Results are reported whichever way they point.

**T1. Are SEC preseason rankings unjustified?**
- Unit: every team ranked in a preseason (week-1) AP poll.
- Final standing: the team's season-only rating rank after the last regular-season week, capped at 26 (26 = outside the results top 25).
- Shortfall = capped final rank − preseason AP rank (positive = finished below where it started).
- Fairness adjustment: higher-ranked teams have further to fall, and conferences differ in how many top-10 teams they have. The expected shortfall for each preseason rank comes from a straight-line fit of shortfall on preseason rank across all conferences. **Primary measure:** mean of (shortfall − expected) by conference, and SEC minus ACC. Also reported: raw mean shortfall, and the share of preseason-ranked teams that finished outside the results top 25.
- **Supports the claim** if the SEC's adjusted shortfall is above zero with an interval excluding zero, and SEC minus ACC is above zero with an interval excluding zero. **Partial** if only the first holds. **Refutes** if the SEC's adjusted shortfall is at or below zero.

**T2. Does the SEC's schedule boost come from early-season rankings?**
- Unit: every regular-season game of an FBS team. Per game: opponent's AP rank points in the poll before the game minus opponent's final season-only rank points (26 − rank inside the top 25, else 0; FCS opponents 0 on both sides). This is the per-game version of H5 variant B, in rank points (one point = one place inside the top 25).
- Bands by schedule week: early 1–4, middle 5–8, late 9 and later.
- **Primary measure:** mean per-game gap by conference and band; SEC early minus SEC late; SEC minus ACC in each band.
- **Supports a preseason link** if the SEC early-band gap is above zero with an interval excluding zero, and SEC early minus late is above zero with an interval excluding zero. **No link shown** if the SEC gap is flat across the season or larger late.

## 2026-10-23 — T3: the in-season "ranked loop" (Kyle's request; added after all earlier results)

Proposed after T1 and T2 to explain them. Hypothesis: when ranked teams in the same conference play each other, the loser falls less than its season justifies ("good loss") and the winner gains credit for beating a ranked team, so the conference keeps its teams ranked above their results all season. Definitions and readings are fixed here, before it is run. Data: 2014–2025 (no 2020), regular season, rows with exactly one game that week. Intervals: 1,000 resamples of team-seasons, seed 0. Results are reported whichever way they point.

- **Post-game overrating** = the team's final season-only rank after the last regular-season week (capped at 26) minus its AP rank in the poll right after the game (26 if unranked). Positive = after that game, the poll ranked the team above where its season ended up.
- **Adjustment:** a team's starting point matters (higher-ranked teams have further to fall), so for each group of games the expectation comes from a straight-line fit of post-game overrating on the pre-game AP rank across all conferences. Means of (actual − expected) are reported by the team's conference.

**Primary (the loop's losing side):** ranked teams that lose to a ranked opponent from their own conference. **Supports the loop** if the SEC's adjusted value is above zero with an interval excluding zero and SEC minus ACC is above zero with an interval excluding zero. **Partial** if only the SEC is above zero. **Not supported** otherwise.

**Controls** (same measure; separate the loop from general SEC overrating):
- C1: ranked teams that lose to a ranked opponent from another conference.
- C2: ranked teams that lose to an unranked opponent.

The loop is specific to the conference only if the SEC effect in the primary group is clearly larger than in C1 and C2 (reported as SEC primary minus SEC C1, with interval).

**Secondary (the winning side):** ranked teams that beat a ranked opponent from their own conference, same measure.

Also reported for each group: share still ranked in the next poll, and average places dropped (or gained). Every qualifying game is saved to `results/t3_loop_games.csv`.

## 2026-10-23 — T4: does the season-only rating overrate the SEC? (Kyle's request; added after all earlier results)

Kyle's objection: the finding that SEC schedules are tougher by results may itself be biased. SEC teams mostly play each other, so how strong the SEC looks to any rating rests on its games against outsiders. If those games flatter the SEC, the rating overrates the whole conference and every SEC schedule looks harder than it is. This test referees that with games outside the conference, including bowls, which the rating never saw. Fixed here, before it is run; reported whichever way it points.

- **Games:** every completed game, 2014–2025 (no 2020), between an SEC team and an FBS team from another conference. Regular-season games from week 4 on (earlier ratings rest on too few games), plus all postseason games (bowls and playoff). FCS opponents excluded.
- **Prediction, made before each game:** the performance component of the season-only rating, which is on the scoring-margin scale. Predicted SEC margin = SEC team's rating − opponent's rating + home edge (+ if the SEC team is at home, − if away, 0 if neutral), from ratings through the previous week. Postseason games use the final regular-season ratings, so the rating has never seen them.
- **Primary measure:** mean of (actual SEC margin − predicted margin), with actual margins capped at ±28 like the rating itself. 95% interval from 1,000 resamples of SEC team-seasons (seed 0).
- **Reading:**
  - **Supports Kyle's objection (the rating overrates the SEC)** if the mean is below zero with an interval excluding zero. SEC teams then do worse against outsiders than the rating expects.
  - **Refutes it** if the mean is at or above zero with an interval excluding zero (the rating, if anything, underrates the SEC).
  - **Inconclusive** if the interval includes zero.
- **Also reported:**
  - the same measure for every other conference against outsiders, for comparison;
  - postseason games alone, which the rating never saw;
  - games against power-conference opponents alone (ACC, Big Ten, Big 12, Pac-12 through 2023, Notre Dame), to address the "cupcakes" concern;
  - the share of games the SEC team won against the number predicted;
  - a raw, model-free head-to-head of SEC against ACC: record and average margin, regular season plus postseason.

Every game used is saved to `results/t4_referee_games.csv`.

## 2026-10-31 — 2026 data re-frozen through week 8 (Kyle's request)

The 2026 season was frozen on 2026-10-23 through week 7 (AP poll 8). Week 8 games and AP poll 9 are now available. The methodology's 2026 analyses cover "all completed weeks", so the 2026 files are re-pulled. **Only the 2026 files change.** The upstream copies of the historical schedule files were checked and are byte-identical to the frozen ones; no historical file is touched, and nothing from 2014–2025 changes.

- **Schedules:** `cfb_schedules_2026.parquet` from sportsdataverse/cfbfastR-data at commit `2f9c0044`. The other 12 files stay at `09f2595e`. The manifest now records the commit for each schedule file.
- **Polls:** `rankings_2026_regular.json` and `rankings_2026_postseason.json` re-pulled. The regular-season file holds AP polls 1–9. The manifest records the frozen poll week, which `src/fetch_data.py` reads instead of a hard-coded week.
- **What changes:** every 2026 output (the counterfactual, the over/underrated board, 2026 schedule strength and the 2026 figures) is recomputed through week 8 and poll 9, and the report's 2026 numbers are updated to match. The week-7 versions remain in git history.

## 2026-10-31 — T5: is the SEC ranked so high because of its results? (Kyle's request; added after all earlier results)

Kyle rejects the conclusion that the SEC does not benefit from bias "unless we can show with data why the SEC is ranked so high", with ranking-independent data showing its strength of record. This test answers that. The design was drafted, reviewed by three independent reviewers (fairness to both sides, statistics, ranking-independence), merged into 14 changes, and is fixed here before any T5 count is computed. The code that will run is commit `e03ebb2` (`src/sor_test.py`). Results are reported whichever way they point.

**Disclosures.**
1. T5 was designed after H2 (SEC +1.11 places against the season-only rating) and T1–T4 were seen.
2. During design review, one reviewer computed approximate excess against the *performance* top 25: SEC about +0.08, ACC about −0.19, SEC minus ACC about +0.27 slots per poll; SEC about +0.36 in polls 6–9 and about −0.10 in polls 10+. The performance check is therefore not blind. It is descriptive only. SOR, Colley, rank points and both baselines are unseen.
3. Candidate sigmas were computed: SD of errors 16.7, probit 14.1. These are not outcomes.
4. Expected precision: SEC half-width about 0.4 slots per poll; SEC minus ACC about 0.75; the minimum detectable SEC-minus-ACC difference at 80% power is about 1.0 slot per poll. An inconclusive comparison is not evidence of bias, and not a clean bill either.

**Inputs (ranking-independent).** That season's scores, home/away/neutral site and who played whom, through schedule week w (the week before AP poll w+1), plus each school's FBS/FCS status. All FCS opponents form one pooled team. Two constants are shared by every team and season: the ±28 cap and sigma. No polls, preseason, prior-season results, names or conference labels enter any rating or SOR. Conference is used only to count teams after the rankings are built; the T4-offset check below is the one labelled exception. One game is moved: a kickoff on Sunday at 2 pm ET or later in week 2+ comes after that week's AP poll and counts from the next week. On this data that is only 2016 Georgia at South Carolina (Hurricane Matthew). Week-1 Labor Day games precede the Tuesday poll and are not moved. The rebuilt performance ratings match `season_ratings.csv` to within 1e-13 everywhere except that one week.

**Measures, rebuilt after every week w ≥ 5 that has an AP poll w+1.**
- **Performance:** the season-only margin rating.
- **Colley:** the wins-and-losses rating; shares no margin information.
- **SOR:**
  - Benchmark = mean performance rating of the 25 best FBS teams that week.
  - Win chance against each opponent = Φ((benchmark − opponent + home edge × venue)/σ).
  - SOR = P(benchmark wins at least as many of the team's games as it did), by Poisson-binomial.
  - **σ = 14.102 points:** a no-intercept probit of home win on the pre-game predicted margin, FBS vs FBS, weeks 4+, 2014–2025, 6,520 games, fixed.
- **Ranks:** average ranks for ties.
- **End of regular season:** the last week w with an AP poll w+1. The post-bowl poll is never used.

**Groups.** SEC, ACC, Big Ten, Big 12, Pac-12 (2014–2023 only), Notre Dame (reported on its own, left out of the power average), Other. Membership is by season (Texas and Oklahoma count as SEC from 2024).

**Ties at 25th.** Each of k teams tied for the last m slots counts m/k, so every poll has exactly 25 slots per side.

**Primary.** Per season, polls 6+:
- E_G = mean over polls of (AP top-25 slots − SOR top-25 slots) for group G.
- E_SEC.
- D_PWR = E_SEC − the mean of E for ACC, Big Ten, Big 12 and Pac-12 (when present).
- D_ACC = E_SEC − E_ACC.

**Inference across the 11 seasons:**
- 95% interval = mean ± t(0.975, 10)·SD/√11.
- 90% interval = mean ± t(0.95, 10)·SD/√11.
- The number of positive seasons.
- An exact sign-flip test over all 2,048 sign patterns.
- A seed-0 season bootstrap, as a secondary check only.

**Reading.**
- **Part 1, the SEC against its own record:**
  - (a) **OVER-RANKED** if the 95% interval of E_SEC is wholly above 0 and at least 9 of 11 seasons are positive. Labelled **SEC-SPECIFIC** only if D_PWR passes the same rule; otherwise **SHARED WITH THE OTHER POWER CONFERENCES, NOT SEC-SPECIFIC**.
  - (b) **CONSISTENT WITH RESULTS** if the 90% interval of E_SEC lies wholly within ±0.5 slots per poll. If (a) also holds: over-ranked by less than half a slot per poll.
  - (c) **UNDER-RANKED** if the 95% interval is wholly below 0 and at most 2 of 11 seasons are positive.
  - (d) **INCONCLUSIVE** otherwise.
- **Part 2:** D_ACC is higher, lower or inconclusive by the same 95% plus 9-of-11 rule.

**Robustness gate.** A label is robust only if, for each of E_SEC, D_PWR and D_ACC, the sign (or, for "consistent", a point estimate within ±0.5) holds across all of these:
- all 9 combinations of σ × (0.75, 1, 1.25) and benchmark (top-12 mean, top-25 mean, 25th team);
- both T4 offsets: each conference's T4 mean residual added to its teams' performance ratings, (i) all games: SEC +3.35, ACC +0.13, Big Ten +3.49, Big 12 +4.17, Pac-12 +0.80; (ii) against power opponents: SEC −0.22, ACC −3.10, Big Ten +3.05, Big 12 −0.31, Pac-12 +0.65; others 0;
- rank points (26 − place inside the top 25, ties averaged; each side sums to 325);
- the Colley top 25;
- the end-of-regular-season SOR top 25 (foresight: AP at poll w+1 against the final record).

**Descriptive** (no claim language):
- the performance top 25 (not blind; see disclosure 2);
- headline levels per group: average teams per poll in the AP top 25, the SOR top 25 and the SOR top 10, per member team, plus the share of AP top-10 slots held by teams also in the SOR top 10;
- the SEC-minus-ACC SOR top-25 count with a t-interval;
- week bands (polls 6–8, 9–11, 12+, end of regular season);
- a team-level gap (SOR rank capped at 26 minus AP rank), with whole-season resampling;
- a **noise baseline:** per season, final performance ratings are treated as truth and every game is simulated 200 times (seed 0) with that season's margin noise; expected excess = top 25 by true rating minus simulated SOR top 25; observed minus baseline reported with a t-interval.

**2026 (descriptive).** A table of every team in AP poll 9 or the SOR, Colley or performance top 25 after week 8, sorted by SOR rank, with each team's SOR rank range across the 11 variants. The poll-9 E_SEC, E_ACC and D_ACC are shown with their rank among the historical poll-9 values. No test.

**Published:** `results/t5_sor.json`, `results/sor_weekly.csv` (every team-week's SOR, Colley and performance ranks and record; no poll data) and `results/sor_2026.csv`.

## 2026-10-31 — T6: were SEC teams ranked higher early than their season justified? (Kyle's request)

Kyle asked whether SEC teams were ranked higher in the early weeks than they should have been, or whether their preseason rankings hold up less often than other conferences', which would point to hype driving the preseason poll. T1 asked a version of this with the combined rating and mainly the ACC as comparator. T5 starts at poll 6. This test asks it directly, with ranking-independent measures and the T5 framework. It was designed and logged **before any T5 result was seen**: the T5 run finished in the background unread, and its notice was cancelled so this entry stays blind. The code that will run is commit `3643a3b` (`src/early_test.py`). Results are reported whichever way they point.

**Comparison.** For each season 2014–2025 (no 2020): AP polls 1–5 (the preseason poll and the next four) against the **end-of-regular-season** top 25 by results-only measures. These are built exactly as in T5 from that season's games through the last regular-season week with an AP poll after it: strength of record (σ = 14.102, top-25 benchmark), Colley wins-and-losses, and performance. Groups, membership, tie rules and the late-game move are as in T5.

**Primary.** E_G = mean over polls 1–5 of (AP top-25 slots − final-SOR top-25 slots). E_SEC, D_PWR (E_SEC minus the mean of ACC, Big Ten, Big 12, Pac-12 when present) and D_ACC (E_SEC − E_ACC). Statistics as T5: t-intervals over 11 seasons, positive-season count, exact sign-flip test, and a season bootstrap as a secondary check.

**Reading** (T5's rules, early wording):
- **Ranked higher early than the season justified** if E_SEC's 95% interval is wholly above 0 with at least 9 of 11 seasons positive. SEC-SPECIFIC only if D_PWR passes the same rule; otherwise shared with the other power conferences.
- **Early rankings consistent with how the season turned out** if E_SEC's 90% interval lies within ±0.5 slots per poll.
- **Ranked lower early** if the 95% interval is wholly below 0 with at most 2 of 11 seasons positive.
- **Inconclusive** otherwise.
- **Part 2:** D_ACC higher, lower or inconclusive by the same rule.

**Robustness gate:** the sign holds across all 9 σ × benchmark cells, both T4 offsets, rank points, the final Colley top 25 and the final performance top 25. The performance check is blind here: the earlier non-blind computation covered polls 6+ only.

**Also reported:**
- The preseason poll alone (descriptive).
- **T1 redone with strength of record:** for every preseason-ranked team, final SOR rank (capped at 26) minus preseason rank, adjusted by a straight-line fit across all teams on preseason rank. Per-season mean by group gives A_SEC, D_PWR and D_ACC with the same t-statistics; the "hyped" reading uses the same 95% plus 9-of-11 rule. Also: share of each group's preseason-ranked teams finishing outside the final SOR top 25.

**Caveat stated with the result.** Early polls reflect what voters knew then (returning players, coaching changes). "Not justified by how the season turned out" measures hype in hindsight; it is not proof of intent. Every conference's early picks regress somewhat, which is why the SEC is compared with the other power conferences.

## 2026-10-31 — Corrections after the T5/T6 audit (no logged number changes)

After T5 and T6 ran, an independent audit checked both scripts against their entries above, hunted for bugs and checked how the results were described. Each finding was then checked by two skeptics asked to refute it. No bug changed a logged number: T6 reruns byte for byte apart from the added fields, and T5's logged numbers are unchanged apart from the added fields. These changes are made before the reruns that use them.

**1. Robustness verdict per label (was missing).** The code wrote a sign check for each quantity but never applied the logged rule ("a label is robust only if, for each of E_SEC, D_PWR and D_ACC, the sign holds across all of these"). The run commits read the gate on E_SEC alone for Part 1. That was wrong. Under the logged rule:
- **T5 Part 1: not robust.** D_PWR turns negative under the T4 all-games offset (−0.04), and E_SEC falls from +0.68 to +0.08 there.
- **T5 Part 2: not robust.** D_ACC turns negative under both T4 offsets (−0.56 and −0.20).
- **T6 Part 1: not robust under the literal rule,** because D_ACC turns negative under the T4 all-games offset (−0.15). E_SEC and D_PWR keep their sign in all 14 checks (E_SEC at least +0.93).
- **T6 Part 2:** inconclusive, and not robust.

The scripts now write `label_part1_robust` and `label_part2_robust`, and list the checks where each sign flips.

**2. Gate summary units.** The min/max and the ±0.5 band check mixed rank points (each side sums to 325) with slot counts. They now use slot checks only, and rank points are reported on their own.

**3. T6 outputs the logged pieces it left out.** It now writes the "hyped" reading for the preseason shortfall (result: NOT SHOWN) and the caveat the log requires with the result.

**4. Two descriptive additions, post hoc, after results were seen; no claim language.**
- **(a) T5 week bands measured against the end-of-regular-season record** (T6's yardstick). Every stage of the season is then measured the same way. The logged bands measure against the record to date, which gives polls 6–8 a different yardstick from polls 1–5.
- **(b) A T6 decomposition of each group's early excess** into three parts: the drop out of the final top 25 expected for teams at those AP ranks (rank buckets of five, pooled over all teams and seasons), the drop beyond that, and unranked teams entering the final top 25.

**5. The "noise baseline" is described accurately from now on.** The audit showed it barely depends on the simulated noise: SEC +1.58 with no noise and +1.52 at the logged SD. What it measures is the built-in gap between a top 25 ordered by strength and a top 25 ordered by record. It is reported as that. The code and the JSON key are unchanged. It is seeded `default_rng([0, season])`, not a single seed 0.

**6. Wording of results, following the audit:**
- T5's "over-ranked" means relative to strength of record. Against the margin-based performance top 25 (descriptive, not blind) the excess is +0.07 (95% t −0.32 to +0.45). Most of the T5 excess is in polls 6–8.
- T6's early excess is reported with the logged hindsight caveat and the decomposition.
- The wide interval on the preseason shortfall is reported as "no evidence of", not as "no shortfall".
- The captions of Figures 26 and 27 are corrected.
- A label branch not reached in any run (over-ranked, consistent and SEC-specific all at once) now says "SEC-specific".

**Refuted by the skeptics, so not acted on:** the claim that "shared with the other power conferences" is contradicted by the data. Taken as the logged bloc (the mean of ACC, Big Ten, Big 12 and Pac-12 when present), the other power conferences pass the same over-ranking rule in T5 (+0.18, 95% t +0.03 to +0.32, 9 of 11 seasons) and in T6 (+0.47, 95% t +0.13 to +0.81, 10 of 11 seasons).

## 2026-10-31 — Descriptive additions for the summary and post (logged after drafting, before publication)

While `SUMMARY.md` and the LinkedIn post were being written and fact-checked, a few descriptive numbers were added to `results/post_numbers.json` (built by `src/post_numbers.py`). They were computed after every result had been seen and were first used in a draft of the summary before this entry was written. They are logged here before publication. None is a test; no logged number changed.

- **SEC minus each other power conference in the strength-of-record top 25** (Big Ten, Big 12, Pac-12), computed from `results/sor_weekly.csv` the same way as T5's logged SEC-minus-ACC figure. The ACC row reproduces T5 exactly (+2.27). SEC minus Big Ten is +0.74 (95% t −0.55 to +2.03; 6 of 11 seasons).
- **The other-power-conference average excess** in T5 (+0.18) and T6 (+0.47), computed per season as E_SEC − D_PWR. These were computed during the audit and are in the entry above; only their addition to `post_numbers.json` is new. This is the logged bloc, the mean over conferences, not a combined count.
- **Miami's 2026 schedule rank among power-conference teams** by opponents' 2026 results (48th of 67).
- **The mean strength-versus-record gap** for the SEC from the T5 "noise baseline" (1.46 slots per poll).
- **T6 decomposition shares**: the share of SEC early spots that miss the final top 25 (38.6%) and the share expected at those AP ranks (37.7%).
- **Pass-through values** already in result files: T2 SEC minus ACC per band, H5 variant B for the Big 12 and Big Ten, T4 for the other conferences, T5 and T6 values under each calibration, T3 values before the rank adjustment.

Two rounds of fact-checking (checkers per document, hostile readers, and skeptics asked to refute each issue) reviewed the summary, the README and report changes and the post against the result files. Their fixes changed wording and added caveats. No result was recomputed.

## 2026-10-31 — Calibration check of the schedule and poll-place results (descriptive, added before publication)

**Why.** The final fact-check of the post found a double standard. T5 and T6 were checked against two calibrations of the results rating, each conference shifted by its average T4 residual against outsiders (all games, or power-conference opponents only). The schedule results (H5 variant B, T2) and the poll-place gap (H2 on the season-only rating) rest on the same rating but were never checked that way. A fact-checker reran them with the calibrations before this entry was written, so the numbers had been seen. `src/calibration_check.py` now does it reproducibly and writes `results/calibration_check.json`. The code of each test is unchanged; only the rating's performance half is shifted, then the 50/50 combined rating and its rank are rebuilt as in `src/season_rating.py`. Uncalibrated, it reproduces the published numbers exactly. It also splits the Pac-12 (2014–2023) out of "Other" in H5 variant B.

**What it shows** (SEC first; uncalibrated / all-games calibration / power-games calibration):
- **Whole-schedule game-day boost (H5 B), SEC:** +5.69 / +1.59 (95% CI −0.77 to +4.34) / +7.66. The sign holds; it is not clear under the all-games calibration.
- **SEC minus ACC (H5 B):** +3.54 (not clear) / −6.90 (CI −10.99 to −2.92) / −4.60 (CI −8.75 to −0.38). Reverses under both calibrations.
- **Per game (T2), SEC:** positive in every band under every calibration; clear in every band except weeks 9+ under the all-games calibration.
- **Per game (T2), SEC minus ACC:** clear in every band uncalibrated; not clear in any band under the all-games calibration (+0.27, 0.00, −0.33); clear only in weeks 1–4 under the power-games calibration.
- **Poll places above the rating (H2), SEC:** +1.11 / −0.21 (CI −0.92 to +0.47) / +1.51. ACC: +0.35 / +2.57 / +3.97.
- **Pac-12 split (H5 B, uncalibrated):** +5.42 (CI +0.96 to +10.21; 108 team-seasons), about the SEC's size.

**Reading.** Applying the logged robustness rule (a sign must hold in every check): the SEC's own game-day schedule boost holds its sign; every SEC-versus-ACC schedule and poll-place contrast does not, and neither does the SEC's one-place poll gap. These are descriptive and are reported as such.
