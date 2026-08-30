# Data Sources and Player Identity

## Purpose and authority

This document is the authoritative guide to what each data source is used for
and how records from different providers are assigned to the same player. The
product and architecture requirements remain authoritative in
`docs/PROJECT_SPEC.md`; operational commands remain in
`docs/operations/data-source-operations.md`.

The central rule is that identity and data authority are separate questions:

- nflverse/GSIS identifies **who the player is**;
- FantasyPros describes **what the player was projected to do**;
- FFA contributes **uncertainty and complementary projection fields**;
- nflverse statistics describe **what the player actually did in the NFL**;
- Yahoo and the supplied auction history describe **what happened in this
  fantasy league**; and
- `config/league.json` defines **how NFL statistics become JUGG fantasy
  points**.

No provider is authoritative for every field. A provider's identifier is not
evidence that all its names, teams, projections, or results should overwrite
another provider's fields.

## Source roles

| Source | Primary use | Not used as |
| --- | --- | --- |
| FantasyPros preseason projections | Defines the preseason draft-player pool and supplies primary projected counting statistics | Permanent player identity or historical NFL truth |
| FantasyPros consensus rankings | Current non-PPR expert-consensus rank, position rank, tier, and expert range for writeup context | Projection, auction-dollar value, or automatic Target/Avoid vote |
| FantasyPros injuries | Dated current availability, designation, injury detail, practice status, and probability context for writeups | Permanent player trait or automatic valuation adjustment |
| FantasyPros news | Dated recent player developments and FantasyPros impact summaries for writeups | Durable fact after its date, independent analyst vote, or live draft dependency |
| FFA preseason snapshots | Projection uncertainty, kicker detail, injuries, biographical enrichment, comparison, and missing-field fallback | Projection backbone or permanent identity |
| nflverse player registry and rosters | Preferred GSIS identity, cross-provider IDs, and historical/current roster evidence | Preseason projection source |
| nflverse weekly depth charts | Dated team hierarchy, position slot, and depth rank; display-ready QB/RB/WR/TE corps | Fantasy projection, durable role guarantee, or automatic recommendation |
| nflverse player/team statistics and schedules | Primary historical NFL outcomes and league-scored actuals | Live draft dependency |
| FantasyPros historical actual points | Legacy evaluation and equal-cohort provider comparisons | Preferred long-term actual-stat source |
| Historical auction CSV | JUGG sale price, winning owner, player label, position, and season | NFL performance or player-identity authority |
| Yahoo league data | League settings and, when imported, authoritative Yahoo transactions, rosters, standings, and platform IDs | NFL projection or outcome source |
| `config/league.json` | JUGG scoring, roster, auction, and league rules | Player data source |
| Google Sheets | Optional shared view and reporting destination | Draft-state or identity authority |

All network sources are acquired before draft night and preserved locally. The
live draft application consumes validated local artifacts and never requires a
provider to be online.

FantasyPros rankings, injuries, and news are joined through the same canonical
FantasyPros-to-GSIS identity mapping as projections. The AI writeup build reads
only the latest validated local context artifact. Rankings are labeled as
non-PPR consensus context, while injury and news facts retain their timestamps
because they can become stale quickly. None of these feeds silently changes
projected points, expected auction price, walk-away price, or research votes.

## Canonical player identity

An NFL player with a validated GSIS mapping uses:

```text
nfl:gsis:<gsis_id>
```

For example, Josh Allen is `nfl:gsis:00-0034857`. A defense/special-teams unit
uses `nfl:def:<team>`.

FantasyPros, FFA, Yahoo, ESPN, PFR, PFF, and other identifiers are aliases
attached to this stable entity. They are retained for joins and provenance but
do not replace the internal identity.

If a FantasyPros projection cannot be safely matched to GSIS, it remains:

```text
provisional:fantasypros:<fantasypros_id>
```

Provisional does not mean the projection is invalid or the player should be
removed. It means only that the durable identity has not been established. The
record stays separate until new evidence or a reviewed override resolves it.

## Player matching process

FantasyPros defines the preseason population. For each projected player-season,
the identity pipeline uses this evidence in order:

1. **Previously validated GSIS mapping.** Reuse the stable identity, but compare
   it with the latest roster/registry evidence. A disagreement stops
   publication.
2. **Season roster: exact normalized name, position, and team.** This is the
   strongest automatic name-based match.
3. **Season roster: unique normalized name and position.** This handles team
   changes or stale provider team fields when only one candidate exists.
4. **Master player registry: unique normalized name and position.** This
   handles legitimate players missing from the narrower season roster, such as
   free agents, injured/reserve players, or offseason timing gaps.
5. **Reviewed alias plus master registry.** Known naming differences such as
   Hollywood Brown/Marquise Brown are stored with season and position scope in
   `config/player_aliases.json`.
6. **Provisional fallback.** If no unique supported match exists, do not guess.

Names are normalized only to produce candidates: punctuation, accents, common
suffixes, position aliases, and historical team abbreviations are normalized.
A normalized name is never itself a permanent identifier. Fuzzy matches are
not automatically accepted.

### FFA enrichment matching

FFA is matched separately to the FantasyPros-backed projection record. The
order is defense position/team, exact name/position/team, then unique
name/position. Reviewed FFA aliases are source-scoped. FantasyPros remains
authoritative for populated projection fields; FFA fills only absent fields
and retains field-level provenance.

### Auction-history matching

Auction rows use reviewed aliases, then exact name/position/team, unique
name/position in the auction season, and finally a unique stable identity with
the same name/position across seasons. This final step allows a valid purchase
of a player who was injured and absent from that season's projection pool, such
as the confirmed 2021 Gus Edwards sale. Unresolved or ambiguous sales remain
exceptions rather than being forced onto a player.

## Conflict and field-authority rules

- A stable GSIS identity may have different FantasyPros IDs over time; this is
  recorded as a provider-ID transition, not a new player.
- One FantasyPros ID mapping to different GSIS players is a fatal collision.
- A stored GSIS identity disagreeing with current unique roster evidence is a
  fatal conflict.
- Team is time-specific. A preseason provider team and an in-season roster team
  can both be correct for different dates; neither silently overwrites the
  other.
- FantasyPros projected fields win projection conflicts. FFA may fill a missing
  field but may not overwrite a populated FantasyPros field.
- nflverse actual statistics are rescored using `config/league.json`; generic
  provider fantasy-point totals are not treated as JUGG totals.
- Auction price, owner, and season come from league history/Yahoo, not an NFL
  data provider.
- Every derived artifact retains source snapshot and field provenance where
  applicable.

## Review and verification

The pipeline publishes:

- `player_identity_crosswalk.json`: stable IDs, provider aliases, evidence,
  confidence labels, and unresolved exceptions;
- `identity_migration_shadow.json`: old FantasyPros-based IDs beside stable
  GSIS IDs;
- `match_exceptions.json`: unresolved FFA/projection enrichment matches;
- `config/player_aliases.json`: reviewed, source-scoped name aliases;
- `config/player_identity_overrides.json`: explicit reviewed provider-to-GSIS
  decisions; and
- `tests/fixtures/player_identity_audit.csv`: versioned corroborated identity
  checks.

Validation checks collisions, cross-season stability, provider-ID transitions,
auction join coverage, projection-to-actual join coverage, and the reviewed
audit fixture. Confidence labels describe the evidence used; they are not
measured probabilities until a sufficiently large human-adjudicated gold set
exists.

The current audit fixture is a small regression seed, not a complete accuracy
study. Expand it to 300–500 reviewed player-seasons across seasons, positions,
aliases, trades, common names, roster absences, and provisional records before
reporting empirical matching precision.

## Examples

**Stefon Diggs:** absent from the narrow 2026 roster snapshot but uniquely
present in the nflverse master registry. The master-registry fallback safely
assigns his GSIS identity.

**Hollywood Brown:** FantasyPros uses Hollywood Brown while the registry uses
Marquise Brown. A reviewed, season-scoped alias connects the names before the
unique master-registry match.

**Kenny Gainwell:** both current sources use Kenny Gainwell, so no alias is
needed even though Kenneth is a familiar formal name.

**Gus Edwards in 2021:** the auction sale is valid even though injury kept him
out of that season's projection population. His stable identity in other
seasons allows the league transaction to remain attached to the correct player.

## Related documentation

- `docs/PROJECT_SPEC.md`: durable product and architecture decisions
- `docs/operations/data-source-operations.md`: refresh, rebuild, audit, and publication
  commands
- `docs/history/2026-season-record.md`: evidence supporting the accepted 2026
  source roles and links to the detailed final-tag records
- `data/raw/README.md`: raw snapshot inventory and preservation rules
