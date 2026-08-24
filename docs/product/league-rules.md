# League Rules and Scoring

This file records the league-specific inputs used by the draft models. The
machine-readable source is `config/league.json`.

## Auction

- 10 teams with a $200 starting budget per team ($2,000 league-wide).
- Minimum bid: $1.
- No keepers. Yahoo's keeper-management setting is enabled, but it does not
  describe the rules for this draft.
- Every starting and bench roster slot must be filled at the draft, including
  one kicker and one defense/special teams unit.

Each team must draft 14 players: 9 starters and 5 bench players. The live engine
must reserve at least $1 for every unfilled required roster slot. IR is not
draftable and is not counted as a required auction slot.

## Roster

The Yahoo settings screenshot lists:

- 1 QB
- 2 WR
- 1 RB
- 1 WR/RB flex
- 1 WR/RB/TE flex
- 1 TE
- 1 K
- 1 DEF
- 5 bench
- 1 IR

That is 9 starters, 5 bench spots, and 1 non-draftable IR spot per team.

## Historical roster size

- 2020–2024: 8 starters and 6 bench spots.
- 2025 onward: 9 starters and 5 bench spots. The 2025 change converted one
  bench spot into a WR/RB/TE flex without changing the 14-player auction
  capacity.
- IR does not count toward draftable roster size in any season.

## Regular season and playoffs

- The fantasy regular season runs through Week 15.
- Four of the ten teams make the playoffs.
- The semifinal is Week 16 and the championship is Week 17.
- Each playoff round lasts one week.
- There are no first-round byes and the bracket does not reseed.
- Seeds 1–4 are ordered by win/loss record, with total points scored as the
  tiebreaker.
- There are no divisions.

## Offensive scoring

- Passing: 1 point per 25 yards; 5 per touchdown; -1 per interception.
- Rushing: 1 point per 10 yards; 6 per touchdown.
- Receiving: 1 point per 10 yards; 6 per touchdown. No reception points are
  shown, so this is treated as non-PPR.
- Return touchdown: 6.
- Two-point conversion: 2.
- Fumble lost: -2.
- Offensive fumble-return touchdown: 6.

Fractional and negative scoring are enabled.

## Kicker scoring

- Made field goal: 3 points from 0–49 yards; 4 points from 50+ yards.
- Missed field goal: -0.5 from 0–49 yards. No 50+ miss penalty is shown.
- Made extra point: 1; missed extra point: -0.5.

## Defense/special-teams scoring

- Sack: 1; interception: 2; fumble recovery: 2; touchdown: 6.
- Safety: 2; blocked kick: 2; kickoff/punt return touchdown: 4.
- Points allowed: 10 for 0; 7 for 1–6; 4 for 7–13; 1 for 14–20; 0 for
  21–27; -1 for 28–34; -4 for 35+.
- Extra-point return: 2.

## Source

Captured from the supplied Yahoo settings screenshot and the user's explicit
rules on 2026-08-23. User-provided rules take precedence over conflicting or
merely enabled platform settings.
