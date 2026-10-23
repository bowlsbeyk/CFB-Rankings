# Deviations from METHODOLOGY.md

Each entry is dated and committed before the change it describes is used.

## 2026-10-23 — CFBD polls stop at #25 (no "others receiving votes")

**What the methodology says:** teams with no votes count as 0 points; the target is the week-to-week change in AP points.

**What the data shows:** every CFBD AP poll from 2014 through 2026 lists ranks 1–25 only (26 entries when two teams tie at #25). Teams that received votes but finished outside the top 25 do not appear, so their points are unknown, not zero. Checked by `src/verify_data.py`.

**Effect:** a team moving between #26-ish and the top 25 looks like a jump from or to 0 points, which overstates movement at the bottom edge of the poll.

**Decision:** pending Kyle's choice before any modeling. Options:
1. Keep the 0 rule as written and state the limitation.
2. Censored floor: give an unranked team a value below that week's #25 point total.

Other open questions, resolved with no deviation:
- Name matching: every AP-ranked school in every season matches a team in the cfbfastR-data schedules.
- Preseason poll: CFBD regular-season week 1 is the preseason poll in every season (e.g. 2025 week 1 has Texas #1; after Texas lost in week 1, week 2 has Ohio State #1).
