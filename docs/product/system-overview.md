# Renegade Draft Room — Simple System Overview

## What we built

Renegade Draft Room is a league-specific auction assistant. It combines player
projections, past JUGG drafts, current draft conditions, and your personal
preferences to help answer three questions:

1. What will this player probably cost in our league?
2. How much will this player help my roster?
3. At the current price, should I buy, pass, or pivot?

The application does not enter bids or make purchases automatically. It gives
you a disciplined plan, while you remain responsible for nominations and final
sales.

## How everything fits together

```text
Source data
    ↓
Clean, match, and score each player
    ↓
Estimate auction price and football value separately
    ↓
Load the prepared results into the local draft room
    ↓
Recalculate advice as players are nominated and sold
    ↓
Show a price ladder, walk-away point, alternatives, and upcoming targets
```

### 1. Source data

We currently use:

- **FantasyPros** for the main preseason player list and projected stat lines.
- **nflverse** for prior-season actual stats and durable player identification.
- **Yahoo and ESPN ADP** as signals of the broader fantasy market.
- **ESPN Salary Cap Values** as one public auction-price reference.
- **JUGG draft history from 2020–2025** to learn how our league actually pays.
- **FFA** as a secondary projection and enrichment source where useful.

Each source is preserved separately. We do not silently blend two providers or
pretend that ADP, public auction values, and JUGG prices mean the same thing.

### 2. Player matching and stat calculations

Before modeling, the system matches records from different sources to the same
player. It prefers stable NFL identifiers and leaves uncertain matches visible
for review rather than guessing.

It then calculates fantasy points using JUGG scoring. Player Details displays
traditional stat-line tables for:

- last season's actual production; and
- this season's projected production.

Rookies or players without valid prior history show missing actuals instead of
made-up values.

### 3. The values and rankings

These numbers answer different questions and should remain separate:

| Measure | What it means |
| --- | --- |
| Expected JUGG price | What the player will probably sell for in this league |
| Price range | A reasonable band around that expected sale price |
| Projected points | Expected fantasy production under JUGG scoring |
| Production value | How the player's football production converts to auction value |
| Points above replacement | How much better the player is than a likely replacement |
| Position rank | Where the player ranks in projected production at his position |
| Production tier | Players with meaningfully similar projected production |
| Auction tier | Players with meaningfully similar expected JUGG prices |
| Edge | Production value compared with expected price |

The two tier systems are intentionally different. A player may share a
production tier with another player but sit in a cheaper auction tier. That is
one of the clearest ways to identify a possible bargain or replacement.

## Core and supplemental metrics

### Core metrics — these drive decisions

These five metric families determine what the application recommends. They are
the prominent tiles directly beneath the player's name.

| Core metric | Decision it answers |
| --- | --- |
| **Live expected price and range** | What will the room probably charge? |
| **Points above replacement** | How much production do we lose if we settle for a replacement? |
| **Scarcity and fallback** | Can we wait, who is next, and what will waiting probably cost? |
| **Buy-versus-pass outcome and scenario support** | Does buying improve our attainable roster, and how often do the tested paths agree? |
| **Recommended range and walk-away price** | Through what price does the plan remain supported, and when should we pause to recalculate the tradeoffs? |

The shared walk-away price is the recommended stopping point, not a legal cap. The price
ladder is another view of that same decision—not a sixth core metric.

### Supplemental metrics — these explain the core metrics

Supplemental information helps the user understand, verify, and challenge the
recommendation. It should be visually quieter and must not compete with the
five core tiles.

| Supplemental information | How it helps |
| --- | --- |
| Projected points and projected stat line | Shows the expected football production behind replacement value and roster outcomes |
| Prior-season actual stat line | Provides historical context without overriding the projection |
| Position rank | Gives quick orientation within the position |
| Production tier and tier details | Explains the scarcity/fallback summary |
| Production value | Converts projected replacement-adjusted production into dollars for comparison and backtesting |
| Model surplus | Compares production value with expected price; useful evidence, not the final bid limit |
| Pre-draft expected price | Shows the frozen baseline before live room adjustments |
| Auction tier | Summarizes similarly priced players |
| ADP and public auction values | Explain broader-market expectations feeding the price model |
| Bye week and risk flags | Qualify roster fit and confidence |
| Owner tendencies and competing-team pressure | Add probabilistic room context |
| Personal preference adjustment | Shows exactly how saved strategy moved an otherwise calculated checkpoint |
| Source freshness, missing inputs, and uncertainty | Tell the user how much confidence to place in the result |

Supplemental metrics may feed a core calculation or explain it, but they should
not create another independent answer to “how high should I bid?”

### 4. The pre-draft models

The **auction-price model** learns from historical JUGG sales and outside
market signals. Its job is to predict price, not player quality. The current
historical test error is roughly $3.15 per drafted player on average.

The **production-value model** starts with projected JUGG points, accounts for
replacement level and positional demand, and converts production into a
separate dollar value.

The **championship model** tests legal roster-completion paths and estimates
how different choices could affect the chance of winning the league. It is
currently shown as a shadow signal because historical preseason projections
have not separated final roster quality strongly enough to justify precise
championship claims.

The **owner-tendency profiles** summarize supported patterns from prior drafts.
They are context, not proof of what another owner will do.

### 5. What changes during the live draft

The pre-draft expected price remains frozen as a reference. Completed sales
create a separate, cautious live-market adjustment. The app also updates:

- available players and remaining tiers;
- every team's roster, budget, needs, and maximum legal bid;
- likely competition for the nominated player;
- replacement options and opportunity cost; and
- attainable roster-completion paths.

Your saved player, NFL-team, risk, roster, and bye-week preferences may make a
small, visible adjustment to your plan. They do not rewrite the market model or
make a player unavailable.

### 6. The recommendation surfaces

For an officially nominated player, the app shows:

- a projected price and full five-band price ladder;
- reasons to draft and reasons to pass;
- comparable alternatives and remaining tier supply;
- a deterministic recommended range and walk-away price;
- the budget and roster consequences of bidding above that price; and
- an optional note when the Renegades deliberately revise the plan.

Clicking the walk-away tile opens a pre-bid preview. You can test any possible
winning price and see the remaining budget, later maximum bid, targets that
would become harder to afford, and the current fallback before deciding whether
an intentional overbid is worthwhile.

The **Upcoming Targets** drawer ranks the next eight affordable targets using
roster needs, prices, production, tiers, replacement paths, championship
scenarios, and saved strategy. Each target includes a target price,
walk-away price, fallback, and conditional pivot.

The same roster-path price calculation supplies the nomination ladder,
Upcoming Targets walk-away price, plan edge, and the nomination checkpoint.
Production dollars and production surplus remain supporting evidence rather
than alternative answers to “how high should I bid?”

After draft actions, **What Changed** compares saved decision snapshots and
explains important movement in the top target, championship outlook, or active
ceiling.

### 7. Where AI fits today

The foundation is deterministic and local: the same inputs produce the same
answer, and it works without internet access. The Assistant GM currently gives
simple offline answers from that local state.

The deeper AI layer is not yet connected. Its future role should be to explain
tradeoffs, interpret confirmed room notes, surface overlooked context, and
challenge a decision. It should sit beside the calculated baseline—not silently
replace prices, roster rules, or calculated walk-away points.

### 8. Reliability and recovery

SQLite is the draft-night source of truth. Nominations, sales, budgets,
rosters, walk-away points, corrections, and decision snapshots are saved locally in an
auditable history. Google Sheets is an optional shared view: local work commits
first, and failed sheet updates can be retried without blocking the draft.

The result is one system with three layers:

- **Evidence:** source data, actual stats, projections, and history.
- **Models:** expected price, production value, tiers, and outcome scenarios.
- **Decisions:** live recommendations, ceilings, alternatives, and roadmap.

## The minimum information a recommendation needs

Both the local engine and future AI should receive the same compact decision
packet:

- player identity, position, actual/projected stat lines, projected points, and
  important risk flags;
- live expected price and price range;
- points above replacement, production tier, tier supply, and fallback cost;
- current roster, budget, open slots, maximum bid, and competing-team pressure;
- buy-versus-pass roster outcome and scenario support;
- the recommended range and current walk-away price;
- structured personal preferences and their exact adjustment; and
- source freshness, missing inputs, and uncertainty warnings.

The deterministic engine calculates and enforces the plan. AI should receive
the ingredients and the deterministic result so it can explain, question, or
add confirmed room context without inventing a second hidden value system.
