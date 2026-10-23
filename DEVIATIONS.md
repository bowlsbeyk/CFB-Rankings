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
