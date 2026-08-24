# Renegade Draft Decision Guide

## What are we trying to accomplish?

The goal is not to “win the draft” by collecting the most projected value for
the least money. The goal is to leave the draft in the best realistic position
to win the JUGG League championship.

Our primary draft benchmark is:

> **Maximize robust, schedule-neutral championship equity while avoiding
> preventable losses relative to the realistic draft paths available to us.**

In simpler terms: build the team with the strongest chance to win the league,
given the actual prices, players, and opportunities in the room.

The model does not choose a named draft strategy in advance. It does not assume
that concentrated spending, balanced spending, bargain hunting, or any other
style is best. After every sale, it evaluates what we own, what we can still
afford, and the realistic ways we can finish the roster. The best available
paths should dictate the strategy.

## What does championship equity mean?

Championship equity is the estimated chance that a roster wins the league when
we simulate weekly player outcomes, unknown fantasy schedules, the four-team
playoff field, and the Week 16–17 playoffs.

In a ten-team league, the neutral starting point is 10%. A completed roster
with 14% championship equity projects better than an average roster, but 14%
is not a promise that it will win.

The estimate is uncertain. Small differences should not control decisions.
The app should show a range and a plain-language recommendation instead of
pretending that every decimal point is meaningful.

## How do we know whether the draft was successful?

The final draft scorecard should answer two different questions:

1. **How strong is the roster we drafted?**
2. **How well did we use the opportunities actually available to us?**

The main scorecard should include:

- **Championship equity:** our estimated chance to win the league.
- **Playoff equity:** our estimated chance to finish among the four playoff
  teams.
- **Projected lineup strength:** the points produced by the best legal weekly
  lineups, rather than all bench points.
- **Ceiling:** how competitive the roster becomes in favorable but realistic
  outcomes.
- **Resilience:** how well it survives injuries, projection misses, and
  underperformance.
- **Replacement optionality:** how realistically weak roster spots can be
  improved through free agency.
- **Decision efficiency:** how close our final roster came to the strongest
  roster paths that were realistically available during the auction.
- **Equity regret:** meaningful championship potential lost through avoidable
  decisions. Tiny differences inside the model's uncertainty should not count
  as regret.
- **Auction efficiency:** production acquired relative to cost. This helps
  explain the result but is not the final grade.

A draft can be good even if it does not have the most auction surplus. A draft
can also look like a collection of bargains while still producing a weak
starting lineup or poor championship outlook.

### League-wide draft leaderboard

Throughout the auction, the app should rank all ten partial rosters using the
same schedule-neutral championship-equity model and realistic completion
paths. This should be available from a secondary page, drawer, or modal and
should recalculate after every sale. At the end of the auction, the same view
becomes the final completed-roster leaderboard. The primary competitive target
is:

> **Finish first in robust schedule-neutral championship equity at the end of
> the draft.**

The leaderboard should show rank, championship-equity range, playoff equity,
scenario support, and the largest roster strengths and risks. It must use the
same assumptions for every team. The Renegades should be highlighted, and the
scorecard should show the gap between us and the first-place roster.

Finishing first is the goal, but the ranks must respect uncertainty. If two
teams' equity ranges overlap materially, the app should label them as
statistically close rather than claiming that a tiny decimal difference proves
one team drafted better.

The leaderboard measures how well each team positioned itself immediately
after the draft. It does not predict the final standings with certainty and
does not replace in-season management.

## What should appear when a player is nominated?

The nominated-player card should answer three questions immediately:

1. Should I pursue this player?
2. At what prices does that answer change?
3. Why does the answer change?

### 1. Primary recommendation

The top of the card should show one decision band:

- **Strong pursue** — buying is clearly better across most reasonable paths.
- **Lean pursue** — buying is probably better, but the advantage is not large
  or universal.
- **Neutral** — buying and passing are too close or too uncertain to separate.
- **Lean pass** — passing is probably better.
- **Strong pass** — buying is clearly worse across most reasonable paths.

Neutral is the default. The app should only give a strong recommendation when
the advantage is larger than normal simulation noise and holds across most
reasonable assumptions.

During shadow validation, the live card describes support as a count of the
nine tested roster-completion paths (for example, `7 of 9`). This is not a 78%
probability that the decision is correct. The rough equity spread across those
paths remains an internal diagnostic until it is calibrated against the full
championship simulator.

### 2. Price decision ladder

The card should show exactly where the recommendation changes as the auction
price rises. For example:

| If the winning price is… | Recommendation | Why |
| ---: | --- | --- |
| $27 or less | Strong pursue | The player improves nearly every strong roster-completion path while preserving enough money for later needs. |
| $28–31 | Lean pursue | The player still improves most paths, but some cheaper alternatives produce similar outcomes. |
| $32–34 | Neutral | Buying and passing are too close after accounting for uncertainty. |
| $35–37 | Lean pass | The extra cost begins forcing weaker choices at remaining roster spots. |
| $38 or more | Strong pass | Most realistic pass-and-complete paths produce better championship outcomes. |

These thresholds are specific to the current draft state. They can change
after every sale because budgets, opponents' needs, player availability, and
our remaining roster paths change.

The most useful single number is the **recommended maximum price**: the point
where buying stops being meaningfully better than passing. It is not the same
as the expected sale price or the player's general production value.

### 3. Championship effect

At the current price, show:

> If purchased for $31  
> Resulting championship equity: **13–16%**  
> Effect versus passing: **+1.9 percentage points**

The effect versus passing is the important comparison. It asks whether buying
this player now creates better complete-roster outcomes than keeping the money
and pursuing the best remaining alternatives.

Use “percentage points,” not “percent improvement.” Moving from 10% to 12% is
a gain of two percentage points.

### 4. Scenario support

Show how consistently the recommendation survives different reasonable
assumptions:

> **Recommended in 78% of tested scenarios**

Scenarios should vary:

- future auction prices;
- projection sources and projection error;
- weekly volatility and missed games;
- different legal ways to complete the roster;
- conservative, normal, and more active replacement access.

This is called **scenario support**, not “good decision probability.” It does
not mean there is a 78% chance the decision will work. It means the same action
was preferred in 78% of the realistic situations the model tested.

### 5. Market and production context

Keep these values separate because they answer different questions:

- **Expected JUGG price:** what this league will probably pay.
- **Likely price range:** the uncertainty around that expected sale price.
- **Production value:** the player's projected on-field contribution converted
  into dollars.
- **Recommended Renegades maximum:** what we should pay given our roster,
  budget, alternatives, and championship paths right now.

ESPN auction values, Yahoo/ESPN ADP, projections, historical JUGG prices, and
owner tendencies are inputs or context. None automatically determines the
recommendation.

### 6. Plain-language reasons on both sides

Every nomination should include:

> **Draft this player because:** At the current price, he improves our strongest
> attainable roster paths, addresses an important lineup need, and preserves
> enough money for the remaining positions.

> **Do not draft this player because:** Above the neutral-price threshold, the
> purchase forces weaker flex completions, while the best alternatives create
> similar championship outcomes for less money.

The reasons should change when the price crosses a decision tier. The card
should explain not merely that the recommendation changed, but what opportunity
was lost or gained at that price.

### 7. Other live signals

Keep these concise and secondary to the recommendation:

- likely competing owners;
- room pressure and owners who can still bid aggressively;
- best alternatives if the price runs away;
- our remaining roster needs and flexibility;
- relevant owner-tendency evidence;
- bye-week and NFL-team concentration;
- soft player and team preferences;
- expected nomination timing based on ADP.

Preferences remain soft inputs. Liking or avoiding a player, team, situation,
or bye week should influence the explanation and close decisions without
becoming an absolute rule.

## What happens after a sale?

If we win the player, record:

- final price;
- recommendation band at that price;
- pre-purchase and post-purchase championship-equity ranges;
- championship-equity effect versus passing;
- scenario support;
- the main reason the purchase was or was not preferred.

If another owner wins, immediately update that owner's roster and budget,
remove the player from the available pool, and recalculate all attainable paths
and price thresholds. A player we passed on can still improve our outlook if an
opponent overpaid and made future alternatives easier to acquire.

## How should we use the model during the draft?

Use the model as a disciplined decision assistant:

1. Start with the recommendation and price ladder.
2. Watch for the exact price where the recommendation changes.
3. Read the reason for that threshold.
4. Compare the nominated player with the named alternatives.
5. Give more weight to recommendations with strong scenario support.
6. Treat neutral decisions as genuinely close; personal preference may decide
   them.
7. Do not chase small championship-equity differences inside the uncertainty
   range.
8. Recalculate after every sale rather than clinging to a pre-draft plan.

The model should help us adapt intelligently. It should not make us follow a
rigid strategy or imply certainty that does not exist.

## Current limitations

- Historical preseason projections only modestly separated good and bad final
  roster outcomes.
- Historical auction chronology and nominators are not currently available,
  so the existing buy/pass analysis is a price-controlled proxy rather than a
  true nomination-by-nomination replay.
- Historical Yahoo transactions are not yet available, so replacement access
  is tested through conservative scenarios rather than learned manager
  behavior.
- Current simulations still have measurable noise. Approximately 7,840
  simulations per evaluated path are estimated to target a maximum seed range
  near one championship-equity percentage point.

These limitations are why the app should use ranges, scenario support, and
decision bands instead of highly precise claims.

## Final rule of thumb

> Buy a player when doing so produces stronger complete-roster championship
> paths than passing at that price—and stop when the price makes the best
> realistic alternatives stronger.
