Every fall I hear the "S-E-C! S-E-C!" chants. Every week I scroll past the same debates: the SEC is just better, its schedules are tougher. I feel a lot of the same ways about the SEC that fans everywhere else do. And as a Miami fan, when people say we "played nobody," that lands on me too.

So is it true? Is the SEC just better, and do its teams deserve higher rankings because of their schedules? I didn't want another hot take, so I got the data.

How I got it: every FBS game and weekly AP poll from 2014 to 2025 (skipping 2020), plus 2026 so far, from CollegeFootballData.com and cfbfastR. Plus ESPN's ratings, SP+, play-by-play data and bowl results.

What I did: using Python and Claude Code, I ranked every team each week on results alone: no polls, no preseason, no team names. These are plain formulas you can check, not an AI judging teams. Then I paired SEC teams with teams from other power conferences that had the same losses and nearly the same strength of record, and checked who the AP ranked higher. Same test for every conference. I logged each test before running it; three independent reviewers checked the main one.

Two terms matter. Strength of schedule: how good your opponents were. Strength of record: how hard your record would be for a top-25 team against that schedule. Florida: 3rd-toughest schedule by results, 6–4, record ranks 23rd. Utah: 46th schedule, 10–0, record ranks 1st.

What I found:
• The SEC is good. By results alone it puts the most teams in the top 25, about 5.5 a week.
• But with the same record, the AP ranks an SEC team about 2.5 spots higher. An ACC team: about 2.7 lower.
• Part of it is the preseason poll. Head starts carry over, and SEC teams start ahead most often.
• NIL and the transfer portal changed how teams recruit and keep players, so old reputations should count for less. In the polls they don't: the premium was +1.8 spots in 2014–19 and +3.4 since 2021, while the SEC's bowl and playoff record fell from 41–28 to 30–34. The Big Ten won the last three titles.
• "Ranked wins" are partly an echo. SEC teams have 31 wins over teams ranked on game day this year, 29 against SEC rivals. 13 of those opponents aren't top 25 by record today.

What keeps me honest: part of the gap is voters being right. Allowing for how the season ended, about 1.9 of the 2.5 spots remain. ESPN and SP+ rate SEC teams higher than my ratings do. The NIL-era changes aren't statistically clear yet. And this was about the seventh test I ran for an SEC effect, the first with a clear result.

So is the SEC just better? It's good. But a tough schedule doesn't earn extra spots; your record against it should. Same record, SEC teams still get about two more spots midseason, and near the playoff cut line that matters.

And Miami? Through week 11 it's 9–1 with the 3rd-best strength of record. That's not playing nobody.

Data, charts and code:
https://github.com/bowlsbeyk/CFB-Rankings/blob/ccr-10345fd3-h4cky8/SUMMARY.md

#CollegeFootball #CFB
