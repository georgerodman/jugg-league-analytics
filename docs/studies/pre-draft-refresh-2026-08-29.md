# 2026 Pre-Draft Data Refresh — August 29, 2026

## Outcome

The draft-night data and model artifacts were fully refreshed and validated on
August 29, 2026. The accepted rebuild is `20260829T051248Z`; the accepted
auction-price and decision-board build is `20260829T051347Z`.

The active Draft Room database was refreshed in place. Existing test sales,
rosters, preferences, and audit history were preserved. The operator must use
the normal **Reset Draft** control before the real draft to clear the nine test
sales and current test nomination.

Google Sheets was not written during refresh, rebuilding, testing, simulation,
or the local database update.

## Refreshed sources

- ESPN non-PPR salary-cap cheat sheet: provider update dated August 28, 2026;
  280 matched players and exactly $2,000 of auction values for the ten-team,
  $200 format.
- FantasyPros projections: snapshot `20260829T043354Z`, 601 players.
- FantasyPros Yahoo/ESPN ADP: snapshot `20260829T043401Z`, 507 players; the
  provider data reports an August 28 update.
- FantasyPros rankings, injuries, and news: snapshot `20260829T043402Z`, with
  810 ranking rows, 145 injury rows, and 83 news rows.
- nflverse identities and actuals: snapshot `20260829T043413Z`.
- nflverse depth charts: snapshot `20260829T043431Z`; its newest source record
  was timestamped August 28, 2026 at 19:13:13 UTC.

## ESPN comparison

The attached ESPN file was newer than the prior August 19 file. Four players
entered the sheet (DeMario Douglas, Kendre Miller, Malik Davis, and Seth
McGowan), while DJ Giddens, Keon Coleman, Phil Mafah, and Tahj Brooks left it.
Among returning players, 106 ESPN dollar values changed. The largest moves
included Rashee Rice from $40 to $32, TreVeyon Henderson from $8 to $2, Rico
Dowdle from $3 to $7, Ashton Jeanty from $36 to $40, and Garrett Wilson from
$23 to $19.

The importer now accepts a provider PDF with one populated page plus a blank
trailing page while continuing to reject files with multiple populated pages.

## Resulting board changes

The decision board remains 294 visible players. Four newly modeled players
replaced the four players removed from the refreshed source pool. Most price
changes were modest. Two large drops—Evan Engram (-$10.5) and Najee Harris
(-$10.1)—were reviewed in the generated board comparison. Other notable price
moves included Rashee Rice (-$3.3), Josh Jacobs (-$1.7), Saquon Barkley (-$1.0),
and Ashton Jeanty (+$0.5).

Current top examples:

| Player | xPRICE | Likely range | Production value |
|---|---:|---:|---:|
| Jahmyr Gibbs | $74.2 | $68.1–$80.3 | $64.5 |
| Bijan Robinson | $70.2 | $64.1–$76.3 | $57.8 |
| Ja'Marr Chase | $63.6 | $56.4–$70.7 | $33.8 |
| Ashton Jeanty | $45.5 | $39.5–$51.6 | $34.9 |

## Rules and owner boundary confirmed

- Kickoff/punt return touchdowns remain worth **6 points**. Tests and league
  documentation were aligned to that intentional league rule.
- Jordan Flint remains available only as a former-owner historical profile.
  He does not initialize an active 2026 team and is not merged into Ken
  Moller's separate owner history.

## Validation

- Full guarded rebuild: passed and published.
- Python model and importer tests: passed.
- TypeScript type checking: passed.
- Domain suite: 37 of 37 passed.
- Fresh deterministic simulation build `240402e22a80f99d`: 21 of 21 full-draft
  scenarios completed legally with zero failures.
- Simulation checks passed: monotonic price bands, valid fallbacks, and
  recovery equivalence.
- Fresh seed offset: `170000`; the review run did not replace the accepted
  simulation pointer.

The market model selected `ridge:full_without_prior_price` on the held-out
tournament. Its overall median absolute error was $2.07, with an 80th-percentile
absolute error of $5.43. For historical sales of $31 or more, mean absolute
error was $5.28 and bias was -$2.68, so top-end predictions should still be
read with their displayed ranges rather than as exact prices.

## Recovery

The pre-refresh SQLite backup is
`.local/backups/pre-draft-refresh-2026-08-28T235500Z.sqlite`. The normal Draft
Room reset workflow also creates a timestamped backup before replacing local
draft state.
