# Live Market and Renegades Strategy

## Separation of values

Renegade Draft Room keeps three evidence values and one action price distinct:

1. **Pre-draft expected JUGG price** is the frozen model prediction produced
   before the draft.
2. **Live expected JUGG price** adjusts the pre-draft prediction using completed
   JUGG sales. It estimates what the room may pay; it is not intrinsic value.
3. **Production value** estimates the player's fantasy contribution under JUGG
   scoring and roster rules.
4. **Shared walk-away price** comes from the live buy-versus-pass roster-path
   evaluation, then applies any bounded, visible Renegades preference
   adjustment. It is the only actionable willingness-to-pay dollar amount used
   by the nomination ladder, Upcoming Targets, plan edge, and draft checkpoint.

The former Renegades/strategy dollar value remains only as supporting model
context during migration. It does not independently set an action price.

The interface must label these values separately and give a short reason for
material adjustments.

## Live-market adjustment

After every non-voided sale, the runtime compares actual sale prices with the
frozen pre-draft expectations. It calculates a league-wide price multiplier
and position-specific multipliers. Early evidence is shrunk toward `1.0`, so a
single unusual sale cannot reprice the room. Position evidence blends with the
global market and is bounded to prevent unstable recommendations.

Owner budgets, open slots, roster needs, and legal maximum bids affect room
pressure and likely competition. They do not overwrite the historical model.
Voiding a sale removes it from the live-market evidence and recalculates the
view deterministically.

## ADP and nomination pressure

The player list displays a blended Yahoo/ESPN ADP for scanning. The underlying
provider values remain separately available. ADP is evidence that a player may
be prominent on common cheat sheets; it is not presented as a precise auction
nomination-order prediction.

## Bye weeks

Bye week is imported from the 2026 ESPN artifact by stable player identity,
with an NFL-team fallback for players not listed individually. A configured
same-bye threshold may create a bounded recommendation penalty. It never makes
a player unavailable.

## Strategy preferences

The Renegades Strategy drawer stores:

- roster-construction and risk preferences;
- a soft same-bye threshold;
- preferred players and players to avoid;
- preferred or avoided NFL-team situations, optionally limited by position;
- a bounded dollar adjustment for each team rule;
- free-form preferred situations and notes.

Every preference is advisory. Player and team preferences make a bounded,
visible adjustment to the shared baseline checkpoint, appear in the recommendation
explanation, and help order alternatives. They never remove a player, change
the pre-draft or live market estimate, or prevent an explicit nomination or
sale.

Free-form situation notes are persisted for planning and future grounded
Copilot use. Only structured preferences affect deterministic dollar values;
the app does not guess which players match an unstructured description.
