# Fantasy Football Auction Draft Tool — Project Spec

## Purpose

Build a dependable, offline-first assistant for a live fantasy-football auction draft. It should combine league-specific price history, projected player performance, owner behavior, and current draft conditions to recommend decisions in real time without requiring the user to enter every bid.

This document is the durable source of truth for product scope and architecture. Update it whenever the team makes a material product or technical decision.

The consolidated source-authority and player-matching contract is documented
in `docs/architecture/data-sources-and-player-identity.md`.

## Core Models

### Historical auction-price model

Predict the expected sale price or price range for each player in the JUGG
auction. Evaluate publicly available auction-dollar values, ADP, projections,
prior league results, positional markets, rule changes, and eventually owner
behavior as competing and complementary inputs. Select features and model
structure through forward-only historical testing rather than assigning any
provider a privileged role in advance. ESPN's published Salary Cap Value is an
external dollar input; the JUGG prediction is a distinct model output and must
not be presented as ESPN's value or as intrinsic player worth. Every external
dollar value must retain its provider, scoring, roster, team-count, budget,
season, and retrieval assumptions. Evaluate the model with season-held-out
backtests, uncertainty outputs, and transparent baselines.

### Performance-value model

Estimate each player's fantasy contribution under the league's scoring and
roster assumptions, then derive a production-based value that remains separate
from the expected JUGG sale-price model. Keep projected performance, public
auction values, external ADP market signals, historical JUGG sale evidence,
expected JUGG price, and production value separately attributable so the app
can identify likely bargains and overpays without collapsing the signals into
one opaque score.

Reconcile conditional sale prices to the fixed $2,000 league economy by
weighting every supported player's price by the separately modeled probability
that he is drafted. Do not force the 140 highest conditional prices to total
$2,000: that incorrectly assumes the identities of all drafted players are
known in advance and historically compresses premium prices. The production
calibration method must win a forward-only tournament with explicit overall,
$50-plus, and $60-plus error diagnostics.

Assign every player two position-local tiers. The **production tier** groups
players with materially similar projected JUGG points; the **auction tier**
groups players with materially similar expected JUGG sale prices. Tier
boundaries are deterministic natural gaps with bounded within-tier spans, not
fixed player counts. Keep the two tier systems separate so the application can
identify comparable production available in a cheaper auction tier. Recalculate
remaining tier supply after every completed sale and expose it to nomination
recommendations and future draft-roadmap planning.

The runtime player contract also carries normalized 2024 and 2025 actual stat
lines from nflverse when available and a current-season projected stat line from the canonical
FantasyPros-primary projection artifact. Preserve season, games, fantasy points,
counting statistics, and source. Missing prior-season history is explicit for
rookies and other players without a valid prior NFL record; it must never be
filled by guessing or confused with a projection.

The board comparison table shows player age and actual 2025 fantasy points when
available, keeping historical production visibly distinct from projected xPTS.
The expanded player details also carry nflverse birth date and NFL experience
and up to three recent FantasyPros news items from the latest local context
snapshot. News is informational and must remain non-blocking when that local
artifact is missing or stale.
when matched through the durable GSIS identity. Age is calculated from the
birth date at display time; unavailable biography fields remain explicit rather
than being inferred from names or roster status.

Curated fantasy-analysis writeups are supplemental, attributed evidence. Each
source is preserved as a versioned local artifact with author, URL, publication
date, season, and concise player-level paraphrases matched to the canonical
player registry. The runtime imports those takeaways into SQLite and exposes
them in expanded Player Details while remaining fully offline. Analyst labels
and opinions do not silently modify projections, market price, production
value, or the shared walk-away price.

FantasyPros premium consensus rankings, injuries, and news are captured as a
separate versioned local context artifact and may be supplied to the explicit
AI writeup build. Consensus ranks are non-PPR market/analyst context rather
than projections, auction dollars, or player votes. Injury and news items keep
their timestamps and are treated as volatile availability context. These feeds
do not silently alter projected points, price models, walk-away prices, or
Target/Avoid classifications, and the draft board never depends on a live API.

Use FantasyPros as the primary source for the preseason player pool and projected counting statistics. Treat FantasyFootballAnalytics (FFA) and future projection or player-data providers as enrichment sources for uncertainty, kicker detail, injuries, biographical attributes, comparison signals, or missing fields. Preserve every provider independently at the raw-data boundary. Merged model inputs must retain field-level source provenance and apply explicit, tested conflict and fallback rules rather than silently blending or overwriting values.

Use Yahoo and ESPN ADP, acquired through FantasyPros, as historical external market markers. Yahoo ADP comes from the FantasyPros half-PPR ADP source and ESPN ADP from its PPR ADP source; preserve those scoring-context differences. ADP is snake-draft position, not an auction-dollar value.

Use ESPN's published non-PPR Salary Cap Values as a public historical auction-
value input for 2020–2026. Preserve ESPN's stated 10-team, $200-budget context
and keep these values distinct from ADP, projections, JUGG sale history, and the
league's own rules. A source value is evidence, not a JUGG-generated target.

Use nflverse as the primary historical NFL outcomes and identifier-enrichment
source. Preserve nflverse releases as immutable pre-draft snapshots, normalize
them behind a Python adapter, and calculate actual fantasy points from the
league scoring configuration. nflverse actuals evaluate preseason projections
and provide prior-season model features; they do not replace FantasyPros as the
preseason projection backbone. Name-based identity matching must remain
reviewable and must never silently create a permanent player identifier.

Use the nflverse weekly depth-chart release as the source for dated team depth
hierarchies. Preserve the complete season file, publish the newest complete
32-team snapshot as a compact local artifact, and attach players through GSIS
IDs when present. The normalized artifact provides display-ready QB, RB, WR,
and TE groups while retaining the complete source position, slot, rank, and
team chart. A depth rank is roster context, not a fantasy projection, value,
or automatic recommendation input. For 2025 onward, retain the required ESPN
via nflverse attribution and CC-BY-SA license metadata.

Use GSIS-backed internal identifiers (`nfl:gsis:<id>`) as the preferred durable
identity for NFL players and team identifiers (`nfl:def:<team>`) for defenses.
When no validated GSIS mapping exists, retain an explicit provider-scoped
provisional identifier rather than guessing. FantasyPros, FFA, Yahoo, ESPN,
PFR, and PFF IDs are source aliases on that entity, not the entity itself.
Identity promotion requires collision checks, evidence provenance, a shadow
old-to-new mapping, and regression testing against versioned reviewed records.

After a draft is finalized, source snapshots and non-runtime model artifacts
may leave the active repository only after a checksummed season-data archive is
copied to durable storage and the final Git tag exists. The active tree must
retain the complete artifact closure required to view the finalized board,
research, owner context, depth charts, and draft record, plus focused test
fixtures. Refetchable nflverse source files may be restored from the season
archive or reacquired for the next annual rebuild; archived preseason writeups
remain frozen rather than being presented as current research.

The active runtime season, draft ID, SQLite path, and Google Sheets mapping path
are selected through one validated configuration contract. A new season must
use a distinct draft ID and database, begin with Sheets synchronization
disabled, pass its artifact/readiness gates, and preserve rollback to the
finalized prior-season configuration. Manually changing a year in application
code is not an acceptable rollover procedure.

### Owner tendencies

Learn or encode manager-specific behavior from historical drafts: position and team preferences, typical aggression, willingness to pay, timing, nomination patterns, budget discipline, and other repeatable tendencies. Use owner signals as probabilistic context, not certainty, and show when evidence is weak.

## Live Draft Engine

The live engine maintains the authoritative local draft state:

- teams, roster slots, budgets, and remaining needs;
- available, nominated, sold, and undrafted players;
- completed transactions and nomination history;
- market inflation and remaining positional supply;
- continuously recalculated prices, values, recommendations, and risks.

For draft-night coverage, the player search includes a small manual-entry escape
hatch for a missing player. A manual player requires a name and position, with
optional NFL team and bye week. The entry is persisted in the local SQLite
registry and can be nominated, sold, rostered, audited, undone, and synchronized
like any other player. It is explicitly provisional and receives no modeled
price, xPAR, scarcity, walk-away, or championship-impact guidance.

Every completed sale must update the winning roster and budget, remove the player from the available pool, update league-wide constraints, and trigger recalculation. State transitions should be deterministic, validated, persisted, and recoverable.

A deliberate full-draft reset is available from the application. It requires
typing `RESET`, checkpoints and preserves the prior SQLite database as a
timestamped local backup, initializes a clean draft, and projects the empty
rosters to Google Sheets. Renegades strategy and player preferences are
preserved by default but can be reset explicitly from the confirmation dialog.

When every roster is full and no nomination is open, a guarded finalization
action requires typing `FINALIZE`. Finalization appends the audited
`draft_completed` lifecycle event, marks the draft complete and read-only,
disables Google Sheets synchronization for that draft before any later action
can enqueue a remote write, and creates a timestamped self-contained SQLite
backup. A finalized draft cannot be reset or edited through the application.

## Nominated-Player Workflow

### Draft board

The draft board is the canonical draft-night interface at `/`. The former
split-focus Draft Room interface has been retired; `/board` redirects to the
canonical home route so existing bookmarks continue to work. The board uses
five first-class metrics: projected JUGG points (`xPTS`),
points above replacement (`xPAR`), the drop to the next-best available player
at the same position (`DROP`), expected JUGG sale price (`xPRICE`), and the
expected sale-price range. `xRANK` is the cross-position ordering of xPAR.
`DROP` recalculates locally as players leave the available pool. The table also
exposes production tier and the number of players
remaining in that position-tier. Production value remains an internal
analytical conversion of xPAR into league-economy dollars and is not displayed
beside the market-facing xPRICE.

The interface is a full-width sortable player table with a compact sticky
nomination bar. Clicking a player row expands supporting player information in
place without leaving the board. While open, the compact list row is replaced
by an expanded identity-and-action header that carries the primary board
metrics, eliminating a duplicated player row. The compact player row, expanded
player header, and yellow nomination ribbon use the same eighteen-column width
contract, metric order, scale, and separators. The final three decision columns
show xPrice Value, xEquity at xPRICE, and the nomination engine's Target Rank;
players outside the current ranked target set show no target rank. Draft actions sit outside that
shared stat row so they cannot change its column geometry. This preserves
retaining the expanded player's blue state and the official nomination's gold
state. Compact research icons beside player names surface Target, Avoid,
Sleeper, Breakout, Value, and Bust without widening the table. Hover text names
each icon, while the full editable research controls live in the expanded
Fantasy Analysis section. Before a player is officially nominated, the expanded
header places a searchable Nominated By owner picker beside the Nominate button;
the standalone empty-nomination ribbon does not repeat that control. The action
row also shows the player's locally cached nflverse fantasy depth chart (top two
QBs, top three RBs, top four WRs, and top two TEs) beside the nomination action;
the team's current offensive-line rank appears immediately after the TEs using
an ordinal label such as `OLine: 5th`. The rank uses a same-height inline badge:
green for the top 10, neutral for ranks 11–22, and red for the bottom 10, without
reducing the depth-chart text size. Fullbacks are omitted
from the fantasy RB summary. The expanded view also uses an
xPRICE-based roster-impact preview and a single deterministic Decision card
that combines the recommendation, tested-path support, walk-away price,
xEquity, decision edge, production reasoning, and budget consequences. It also includes
the cached fantasy-analysis card summary, close available alternatives, and a
deterministic **Player/Roster Notes** card. That card prioritizes up to six short,
interpreted observations drawn from current roster fit, expected price versus
walk-away price, positional scarcity, alternatives, injury status, bye-week
concentration, research consensus, and tested draft paths. It recalculates
locally with draft state and does not require an AI call. Reusable structured
situation signals also surface top- or bottom-10 offensive lines, top- or
bottom-eight quarterback context, high or limited prior-year target volume,
projected starter or handcuff status, lead/bell-cow versus committee concerns,
and meaningful or contested goal-line work. Every signal keeps its positive or
negative interpretation; historical usage is labeled as prior-year evidence,
and source disagreement may produce competing notes rather than a false single
answer. Player News appears
only when recent news exists and then spans the full width immediately above
the Brief Summary, Value, and Player/Roster Notes cards. It does not leave
an empty placeholder for players without news. The expanded view also includes a full-width
actual-versus-projected stat table. The card-summary tile links to the cached
full writeup in an in-place modal without navigating away from the board.
The modal's research classification controls match the research wiki controls
in button size, spacing, grouping, selected states, and suggestion markers.
The modal has no visible close button; clicking its surrounding backdrop closes it.
The five nomination and sale controls use one consistent keyboard-focus treatment:
a medium-blue control border with a single light-blue outer ring, so their current
position is obvious while tabbing quickly without stacked or mismatched outlines.
During an active nomination, the unmodified `N` key focuses Nominated By and the
unmodified `W` key focuses Winning Owner. These shortcuts are suppressed while
typing, using editable controls, or working in a dialog, and their labels display
visible key hints.
The research wiki and modal use the same writeup content structure; recent news
is excluded from both full writeups and remains available on the expanded player card.
The Value card lists xPRICE and its expected range before the walk-away and
xEquity metrics; Decision edge is not repeated as a tile. It does not repeat a
Great-to-Bad recommendation headline because the official nomination's price
ladder is the canonical display for that classification. The card anchors its
tested-path support, xEquity, budget impact, and reasoning to the player's current xPRICE.
The tested-path sentence matches the decision write-up's body size and highlights
the supported-path count with green, amber, or red treatment for strong, mixed,
or weak support.
The pale-rose news tile uses a muted brick-red accent to remain recognizable
without sharing the active nomination ribbon's yellow state. It omits a redundant
section heading; its headline, date, and update text use the shared 13-pixel
content scale. Brief Summary, Value, and
Player/Roster Notes use consistent 13-pixel headings and 13-pixel prose;
other compact metadata, badges, and metric labels retain their smaller supporting scale.
Within the Value card, the four metric-tile labels use 10 pixels and their
values use 13 pixels for draft-night readability.
The walk-away price remains a separately labeled ceiling, while the price ladder
shows how the recommendation changes at prices above and below xPRICE. The
sticky nominated-player ribbon shows the compact Great-to-Bad ladder on the
same control row as Nominated By, Cancel Nomination, and Enter Winner, using the
scenario engine's price bands. The ladder expands into the available width while
the controls remain grouped on the right. Final sales are entered directly in
this row with a keyboard-ordered winning-owner selector, winning-bid input, and
Enter submit button; pressing Enter from the bid field records the sale without
opening a modal. Each control uses a compact label above its input or button,
including a Price Ladder label above the five colored ranges, and the price-band
cells match the other labeled controls' visual height. Nominated By and Winning
Owner are searchable combo boxes: Winning Owner starts blank when a nomination
begins; typing filters owner and team names, Tab accepts
the first match and advances, Shift+Tab follows the normal reverse control order,
and Enter accepts without submitting the sale. No band receives a separate active
outline; the ladder communicates ranges only. The committed walk-away remains
in the Decision card. The ladder remains
hidden before official nomination and is not duplicated in Player Details. A
collapsible bottom workspace provides three
tables: League Strength, Team Rosters, and Draft History. Team Rosters uses a
searchable owner combo box that filters by owner or team name, then preserves
the authoritative roster-slot reassignment workflow and Google Sheets outbox
synchronization. Draft History preserves confirmed sale reversal and the
immutable audit trail. The unmodified `D` key toggles this workspace while the
draft board has focus. The shortcut is suppressed in inputs, text areas, selects,
editable content, and dialogs so it cannot interfere with owner entry, searches,
bids, or modal work. The drawer toggle displays the shortcut as a visible `D`
key hint. The existing local draft engine, SQLite persistence,
recovery behavior, and Google Sheets adapter remain authoritative and are not
forked for the new interface.

External fantasy analysis is retained as versioned, source-attributed research
with an article-level summary and optional player-level takeaways. It remains
available to the local data layer and is summarized on the draft board using a
simple two-layer vocabulary. `Target` or `Avoid` is the normalized actionable
signal; no action means the research is neutral, tied, or unresolved. `Sleeper`,
`Breakout`, `Value`, and `Bust` are descriptive tags that explain the kind of
argument. Repeated opinions from the same analyst count once in the displayed
positive/negative split. The operator can force Target, force Avoid, hide the
flag, or restore the automatic classification
without changing projections, prices, or recommendation calculations. From the
research wiki, the operator may also independently add or remove Sleeper,
Breakout, Value, and Bust display tags and reset them to their automatic values.
The wiki highlights the currently effective action and tags rather than an
abstract “Auto” state. Suggested actions and tags use a small blue dot in the
button's upper-right corner, while the currently effective choices use a filled
state. The suggestion dot remains visible when the operator makes a different selection. Action
and tag buttons are toggles:
clicking an unselected action selects it, while clicking the selected action
again suppresses the Target/Avoid indicator. When no action is selected,
the starred suggestion remains visible and clicking it restores automatic
behavior. Tags have no separate reset control: clicking a suggested tag that
was manually removed restores its automatic state. Suppressing the flag does
not remove tags, writeups, evidence,
projections, or prices. All manual
classifications are stored separately from the source evidence. Future imports
may update the suggested classifications without overwriting manual choices;
resetting later adopts the newest suggestion.

Player-level aggregate summaries are generated during the repeatable research
build, not during draft-night page rendering. The build uses the stored
takeaways, deduplicated analyst opinions, format and price context, risks, and
source provenance to create two grounded syntheses. The **card summary** (also
called the card writeup) is one or two concise sentences for draft-night
scanning. The **full writeup** (also called the full summary) is one to three
short paragraphs for the longer research brief, using less space when the
underlying evidence is thin. Both outputs are generated together from the same
evidence and cached by an input hash and prompt version. Each retains its source
IDs, model, and generation time. SQLite imports the completed artifact so the
board remains fast and fully functional offline; if a card summary is
unavailable, the interface falls back to deterministic evidence already stored
locally.

All generated prose uses the league's 10-team, non-PPR auction context. PPR
rankings and phrases such as “PPR upside” are not repeated as though they apply
to this league. Reception-driven arguments are translated into their
standard-scoring implications—yardage, touchdowns, total workload, and
price—and recommendations that depend primarily on points per reception are
discounted. This rule applies to card summaries, full writeups, and the separate
Pros/Cons enrichment. Generated prose applies this adjustment silently and does
not mention PPR or compare scoring formats.

Card summaries and full writeups state the fantasy-football interpretation
directly. They do not name analysts or publications and do not use attribution
phrases such as “the analyst says” or “the article argues.” Author and
publication attribution remains available separately through the structured
source links. They also avoid meta-language such as “the evidence suggests,”
“the supplied evaluations suggest,” or “the research indicates.” The prose
should read as a natural, informed fantasy-football assessment; thin support is
expressed through appropriately restrained conclusions rather than commentary
about the underlying source material. When retained sources disagree, the prose
describes a mixed or divided outlook and explains the competing football cases
directly. It does not frame the disagreement as named-person attribution such
as “one analyst says X while another says Y.”

The same structured takeaways and stored full writeups power a local research
wiki linked from the draft-board header. The wiki provides an index, position
sections, direct player anchors, source links, readable long-form entries, and
each player's current position rank, live-adjusted xPRICE, and expected price
range in the header, with team, bye week, and current age immediately below.
The wiki also provides a derived Player Lists section covering lead/bell-cow
backs, primary running-back handcuffs, high-target receivers, quality receivers
paired with strong quarterbacks, quality backs on run-oriented teams, quality
receivers on pass-oriented teams, and players whose team change improved their
quarterback or offensive situation. These lists combine retained research,
current rankings and projections, handcuff mappings, and team context; each
entry explains why it qualified and links to the player's full writeup. Lists
are reproducible derived views and do not create or change Target/Avoid or tag
classifications.
The research wiki and player-card full-writeup modal render one shared writeup
template so identity, opinion summary, Pros/Cons, long-form typography, and
source links stay synchronized. The research-wiki view places current FantasyPros injury and news context in
source-labeled callouts separate from the cached AI prose. The draft-board
full-writeup modal retains the injury callout but omits the latest-news callout
already shown on the player card, stacks Pros above Cons, and places each label
inline with its summary using compact padding. The injury callout
appears only when the structured injury feed has a matching record. In the wiki,
the news callout shows up to three dated items and
labels provider-authored commentary explicitly as `FantasyPros impact` so it
cannot be mistaken for the AI synthesis. Missing context remains silent and
non-blocking; neither callout changes the cached writeup or draft valuation.
Each entry also surfaces separately cached AI Pros and Cons fields. Each field
is one sentence of at most 24 words that synthesizes the two or three strongest
distinct points without changing the card summary or full writeup. Pros/Cons
use 13-pixel text and matching green/red callout treatments in the research
wiki. They retain their own input hash,
prompt version, model, and generation time so an
operator can enrich only missing or stale fields. The interface leaves the
cached full writeup intact and marks genuinely two-sided research as
Mixed when at least one independent positive and negative opinion are present.
One-sided research is labeled Positive or Negative with green or red sentiment
badges respectively;
it remains available without internet access because it renders entirely from
the local SQLite store. It is a derived, reproducible view rather than a second
research store and does not merely repeat the shorter card summaries. PDF or
Markdown exports may be produced on demand but are not part of the normal
research-refresh workflow. Team-level articles are retained as context and may
inform opportunity or environment assumptions, but they do not create a
player-level analyst vote unless the source makes an attributable player claim.
Within each position section, players are ordered by position rank with name as
the tiebreaker; unranked players appear after ranked players.

Research ingestion and AI synthesis are separate operations. New articles and
rankings may be imported without calling an AI model or replacing existing
summaries. The board derives a pending-summary notice by comparing each cached
summary's retained source IDs with current player evidence, showing affected
sources, takeaways, and players until the next explicit batch synthesis. A
dynasty-only ranking is stored as format context and must not create a redraft
positive or negative vote.

Factual research tables such as prior-year player targets, team positional
target shares, analyst accuracy ranks, strength of schedule, and running-back
depth charts are retained in a separate versioned fantasy-context artifact.
Authenticated subscription research may be captured through the operator's
signed-in browser. Player recommendations remain source-attributed takeaways,
while coaching, rookie, transaction, injury, market-share, and red-zone pages
are retained as context and do not create recommendation votes by themselves.
Applicable historical usage, backfield-role, positional schedule, and
offensive-line context is attached to player-summary inputs during an explicit
batch refresh. It may inform the explanation but never creates a Target/Avoid
vote by itself. The synthesis distinguishes prior-year results from current
projections, treats preseason forecasts of 2026 regular-season positional
matchup difficulty as a modest tiebreaker, and
omits contextual facts that are not genuinely relevant to that player's case.
Generated prose calls this the projected regular-season schedule, never the
“preseason schedule.” Exhibition-game schedule strength is irrelevant and is
excluded from synthesis inputs.
Raw statistics appear in generated prose only when the retained inputs also
support an interpretation through a rank, percentile, league or position
benchmark, meaningful trend, or clear football implication. An isolated share,
rate, or count whose quality the reader would have to infer is omitted.
Format-specific advice, such as best-ball or guillotine recommendations, is
retained as labeled player context so it can clarify a future writeup without
changing the standard-redraft Target/Avoid split. External auction exports
retain their scoring, roster, team-count, and budget assumptions; when those
assumptions are missing, their dollar values remain quarantined from JUGG
xPRICE and may be used only as qualified external market context.
The same rules apply to the separate FantasyPros premium context snapshot:
consensus ranking is a non-PPR reference point, while injuries and news are
dated current facts that must not be restated as current after they become
stale. Changing that snapshot invalidates the affected cached writeup inputs
but does not regenerate prose until the operator runs the explicit batch
synthesis.

Setup and administrative controls are grouped under a Draft settings control
beside the application identity. Nomination order and the recoverable full-draft
reset live there, separate from the live Up Next, budget, and max-bid status.
Strategy preferences will use the same settings surface when exposed on the
simplified board.

Scenario paths, championship equity, Assistant GM, owner-tendency guidance,
and roadmap recommendations are not first-class board outputs. Their shared
domain and server implementations may remain available for deterministic board
calculations, testing, and future product decisions, but they do not justify a
second draft-night interface.

Former-owner profiles remain available for historical owner-tendency research,
but profiles explicitly labeled `(former owner)` do not initialize active draft
teams or appear in live owner controls. Replacement owners keep separate
tendency profiles; their histories are not merged.

Optimize the main draft screen around one currently nominated player. Show the information needed to decide whether and how far to pursue that player: projected performance, publicly sourced auction values when available, historical JUGG prices, external ADP, positional context, roster fit, risks, comparable alternatives, and relevant owner signals.

The application is named **Renegade Draft Room** and highlights the operator's
team, **Rodman Renegades**. Its canonical interface is the full-width draft
board described above. The retired split-focus layout is no longer a supported
application surface.

The visual theme is a practical light workspace: white and light-gray surfaces,
blue interaction accents, larger readable typography, restrained borders, and
minimal decoration. Green and red are reserved for positive and negative
decision meaning. Legibility and draft-night scanning speed take priority over
dark-mode atmosphere or decorative styling.

The left player-list pane includes Team Roster as a collapsed bottom bar that
expands upward on demand while preserving the selected owner, roster editing,
and drag-and-drop slot reassignment. Within the right-hand decision workspace,
full-width Player Details appears first, followed by full-width Assistant GM.
Player Details owns projected price, all five price bands, comparable
alternatives, the recommendation, and draft actions. Immediately below the
player name it emphasizes four compact, clickable decision cards: live expected
price and range, points above replacement, scarcity/fallback, and Roster Impact.

The operational player pool includes every current FantasyPros projection row
so an unexpected deep nomination can always be recorded. The validated decision
board remains a separate modeled subset. Projection-backed players outside that
subset are labeled internally as limited guidance, while a small number of
material ADP-only players may be retained without a production projection.
Their unavailable xPRICE, range, xPAR, tier, scarcity, walk-away, and equity
fields display as an em dash; the interface never substitutes a zero-dollar or
one-dollar recommendation. A compact Modeled/Limited/All filter defaults to
Modeled. Limited players remain nominatable, sale-recordable, rosterable, and
sheet-syncable, but they do not enter recommendation paths, modeled alternatives,
or remaining-player championship simulations.
Each card uses one primary-result line and two useful supporting lines. A small
expand indicator communicates that clicking opens deeper evidence without
making the dashboard row taller. Supporting text, price-ladder labels and
ranges, and actual/projected season statistics use a draft-night-readable type
scale. The five-band price ladder spans a separate
compact, headerless section beneath the cards showing Great, Good, Neutral,
Poor, and Bad price ranges. The headerless actual/projected stat table follows
it; the projected season uses an `x` prefix such as `x2026` rather than a
separate Line column. Team Roster uses a tall
QB-through-bench table with bye, paid-price, and production-tier columns,
totals, and remaining max bid. Tier uses the same xPAR-derived Elite, Premium,
Starter, Depth, and Replacement labels shown in the player list and Player
Details; it is not a retrospective grade of whether the auction purchase was
good or bad. Its team selector can
inspect any owner's roster. Filled players can be dragged between legal lineup
slots (or swapped when both resulting assignments are legal); each change is
saved locally as an auditable roster-reassignment event and then projected to
the matching fixed slot in Google Sheets. Likely competition, aligned opponent
needs, room pressure, and supported owner tendencies remain available through
the grounded Assistant GM rather than a permanent League Details panel.

The Scarcity primary card previews the names of its comparable available and
affordable alternatives on hover. Clicking it opens a scan-friendly list of
those players, ordered by projected points, with team, projection, and live
expected price; selecting a name moves Player Details to that player.

Player Details includes blended Yahoo/ESPN ADP. The player list includes bye week and sorts through
clickable, single-line column headers. Position controls include individual
positions, a combined RB/WR view, and a combined RB/WR/TE skill-position view.
The space-efficient player rail always shows sortable projected points, a
named production label derived from xPAR (Elite, Premium, Starter, Depth, or
Replacement),
the frozen pre-draft projected price, live price, and Roster Impact without an
expand/collapse mode. The player rail uses a fixed width so the draft-night
layout remains predictable: it stays at 570 pixels while the adjacent decision
workspace has at least 600 pixels available. Below that combined viewport width,
the player rail becomes a full-width section above Player Details instead of
compressing either pane until its content becomes unreadable.
Roster Impact classifies every
available player at his live expected price as Great, Good, Neutral, Poor, or
Bad, with stronger positive and negative visual treatments for rapid scanning.
The matching primary Player Details card is also named Roster Impact. Its supporting sentence uses plain outcome language—such as “buying creates a better projected final roster in 6 of 9 tested draft paths”—rather than the shorthand “6 of 9 support.” It is a deterministic buy-versus-pass roster outcome
across the nine completion paths, incorporating lineup improvement, roster
need, replacement production, tier scarcity, fallback quality, remaining
budget flexibility, opportunity cost, and bounded personal strategy. Hovering
the result explains the price, role, scenario support, and most relevant
context; Player Details repeats that explanation. Once nominated, the fifth
primary card shows how the outcome changes as bidding rises.
The xPAR Player Details tile retains the precise points-above-replacement value
and adds the same named production label as its plain-language interpretation.
The separate Scarcity tile uses live remaining supply: Unique production, Thin
alternatives, Comparable options, or Highly replaceable. Production labels do
not change as players are sold; scarcity labels do.
Auction tier remains available as supporting context in Player Details but is
intentionally omitted from the player list to reduce scanning noise.
Renegades-specific strategy is stored separately from
market and production models. Preferred/avoided players, preferred/avoided NFL
team-position situations, roster construction, risk tolerance, and bye-week
concentration are bounded advisory inputs: they may make a small, visible
adjustment to the shared walk-away price and recommendations but never make a player unavailable or change the market-price
prediction. Completed sales produce a separate, shrinkage-controlled live
market estimate while preserving the frozen pre-draft prediction. The detailed
contract is in `docs/product/live-market-and-strategy.md`.

There is one authoritative actionable player-dollar checkpoint: the **shared
walk-away price**. It is derived from the live buy-versus-pass roster-
completion price curve, constrained by legal budget and roster flexibility,
then modified only by a bounded and visible personal-strategy adjustment. The
official nomination, Upcoming Targets, plan edge, and initial walk-away price
must use this same amount. Production value and production surplus remain
supporting evidence and backtesting measures; they must not independently set a
competing live action price. Plan edge is shared walk-away price minus live expected
price and is shown only where the full decision ceiling has been calculated.

The permanent metric hierarchy has five core decision families: live expected
price/range, points above replacement, scarcity/fallback, buy-versus-pass
outcome with scenario support, and recommended range/walk-away price. These drive
recommendations and receive primary visual emphasis. Projected and actual stat
lines, projected points, position rank, production value/surplus, production
and auction tier details, pre-draft price, ADP, public auction values, bye week,
risk flags, owner context, personal-adjustment details, provenance, freshness,
and uncertainty are supplemental evidence. They explain or qualify the five
core families but must not appear as competing recommendation outputs.

Player selection is only a private preview and must look unmistakably different
from an official nomination. After the user confirms `Nominate`, the nominated
player's decision card and list row switch to a distinct nomination treatment,
including a persistent **Officially nominated** label and a contrasting accent
or background. Text, iconography, or border treatment must accompany color so
the state remains clear for color-vision differences and under draft-night
glance conditions. The nomination treatment remains until the nomination is
cancelled or its final sale is recorded.

There is intentionally no live bid-entry stream. The user selects or confirms the nominated player, uses the app for decision support while bidding happens elsewhere, then records the final winner and sale price. The app immediately advances state and recommendations.

The final-sale modal uses a keyboard-first owner combobox. Typing any part of
an owner or team name filters the list; Enter or Tab accepts the first match so
the operator can continue through price and confirmation without a pointer.

The header exposes an **Upcoming Targets** roadmap, not merely a background
calculation. It ranks the next eight affordable available players from current
roster needs, expected cost, championship-completion scenarios, positional and
tier supply, replacement cost, and bounded personal-strategy adjustments. Each
target shows its intended role, target price, walk-away price, fallback, and
a conditional pivot. It recalculates locally after every authoritative action.

Every authoritative action also persists a compact decision snapshot. When two
snapshots exist, Player Details exposes a deterministic **What changed** banner
that identifies material movement in the top target, championship equity, or
the active walk-away price. An official nomination creates a persisted
model baseline and walk-away price. The operator may deliberately adjust
that checkpoint with an optional note. A proposed Renegades purchase above it
shows the resulting budget, later maximum bid, and newly constrained targets,
but remains allowed when all league rules are satisfied. Purchases above the
checkpoint remain visible in a discipline audit. Only legal budget, reserve,
and roster constraints are hard stops. These controls guide decisions but never
purchase a player or mutate draft state without explicit action.

The walk-away tile is interactive before bidding. Clicking it opens a read-only
impact preview where the operator can enter any possible winning price and see
the resulting budget, later maximum bid, remaining slots, affected Upcoming
Targets, and current fallback. This preview must not nominate, buy, or otherwise
change authoritative draft state.

Nomination order defaults to owner first-name alphabetical order for 2026 and
is editable in the application. The nominated-by control preselects the next
active owner, while allowing a manual correction; rotation continues from the
owner actually recorded. Owners whose fourteen roster slots are filled are
skipped. The event that fills an owner's final slot creates a persisted draft-
completion record. Active completion order determines waiver tiebreaker order
from first finisher (#1) through last finisher (#10); voiding the completing
sale invalidates that completion and recalculates the active order.

## AI Copilot

The Copilot has two complementary modes:

- Proactive insights: concise, timely alerts about bargains, overpays, scarcity shifts, budget pressure, roster construction, opponent behavior, nomination strategy, and attractive alternatives.
- Chat: natural-language questions grounded in current local draft state, model outputs, historical evidence, and the user's roster goals.

Copilot advice must be explainable and clearly distinguish facts, model estimates, and judgment. AI availability must never be required for core draft operation; the deterministic engine and locally available recommendations remain usable offline.

The V1 layout includes the Assistant GM conversation surface before a remote AI
service is required. Its initial answers are deterministic, local, and labeled
as offline guidance. Connecting streaming AI responses is a later layer and
must preserve that offline fallback.

The grounded Assistant GM uses a versioned, strictly validated context packet
rebuilt server-side from authoritative local state for every request. It is a
read-only explanation layer behind a private provider adapter with no tools or
write capabilities. Responses are state-versioned, streamed, audited locally,
and rejected when stale or when grounding checks fail. The deterministic cards
remain authoritative and usable offline; browser questions and untrusted notes
can never supply or override decision facts. Remote-provider configuration is
optional, server-only, and remains behind a human review gate.
The conversation viewport automatically follows each newly submitted question
and streamed response while retaining independent scrolling for reviewing older
messages. The Assistant GM panel uses only the remaining visible vertical area
below Player Details, with an internally scrolling transcript, persistent
composer, and readable conversation text; it must not extend the desktop
workspace past the viewport. Assistant GM and Draft Outlook are separate peer
panels with matching headers in a shared row: roughly two-thirds of the width
goes to chat and one-third to the scrollable roadmap of current targets, target
prices, and walk-away prices. At narrow responsive widths, the roadmap stacks
beneath the chat.

## Data and Persistence

### SQLite

SQLite is the operational source of truth during the draft. Persist configuration, imported data, model outputs needed at runtime, current draft state, and an auditable transaction/event history. Write locally before initiating external sync. On restart or refresh, reconstruct the exact draft state and identify any pending synchronization work.

Use an immutable, per-draft ordered event log plus transactional materialized
state. Every command carries an idempotency key and expected state version. A
successful nomination, sale, correction, roster reassignment, or lifecycle
change must append its event and update local state in one transaction before
creating retryable remote-sync work. Corrections append compensating events;
they never rewrite or delete audit history. The initial domain and schema
contract is documented in `docs/architecture/draft-domain-and-sqlite.md` and implemented by
`db/migrations/001_initial.sql`.

Decision snapshots, nomination ceiling plans, and discipline overrides are
local SQLite records introduced by `db/migrations/004_decision_planning.sql`.
They remain available after refresh or restart and do not depend on AI, Sheets,
or network access.

Projection imports must be prepared before draft night. The live application reads the last validated local projection artifact and must not call FantasyPros, FFA, or another projection provider during essential draft operation.

### Google Sheets write-through

Google Sheets provides a familiar shared view and optional downstream reporting. Successful local changes should write through to Sheets when connectivity is available. Synchronization must be retryable and idempotent, with visible pending/error status and a reconciliation path. Sheets must not become a runtime dependency or override newer authoritative local state without an explicit conflict policy.

For the 2026 draft, completed sales and compensating sale corrections trigger a
full authoritative roster projection to the `2026 Draft Board` workbook's
`Sheet1` tab. Only each owner's Player and Price cells are written; existing
position labels, formatting, remaining-budget formulas, max-bid formulas, and
salary-cap inputs are preserved. The owner/cell contract is versioned in
`config/google_sheets.json`. The local runtime authenticates with a dedicated
service account whose credential file remains outside version control. Failed
writes remain in the SQLite outbox and can be retried without duplicating picks.

### Offline-first behavior

Prepare all draft-night data and model artifacts locally in advance. Nomination, sale recording, budget and roster updates, recommendations, and recovery must continue without a network connection. Queue remote writes and replay them safely after reconnection. Avoid draft-night dependencies that require package installation, cloud startup, authentication refresh, or live data fetching.

## Deferred Roadmap — 2027 Draft

The league has acquired `texasjuggleague.com`. For the 2027 draft, replace
Google Sheets as the participant-facing draft-board viewer with a live board on
that domain. Each league user should have an authenticated account and, after
signing in, be able to view the current draft board.

This is a future feature and is explicitly outside the 2026 implementation
scope. The website is a read-only participant view unless a later product
decision expands its permissions. It must consume synchronized draft state
through a clearly isolated adapter or service and must not become authoritative
over the local SQLite draft state. Loss of internet access, website hosting, or
user authentication must never block the local nomination and sale workflow.
Google Sheets may remain an optional reporting/export integration after the
website launches, but league members should no longer need to visit Sheets to
follow the live board.

Also explore and implement the following improvements for the 2027 draft:

- Provide a quick, low-friction way to see every team's current maximum bid
  from within the draft application. Candidate presentations include adding
  max bid to an existing draft table or providing a keyboard shortcut that
  quickly opens and closes a compact all-team max-bid view. Choose the final
  interaction after exploring it against the draft-night workflow.
- Make the stat tables on expanded player cards more comprehensive and useful
  for fast player evaluation. Define the additional statistics, comparisons,
  time periods, and visual hierarchy during 2027 product design rather than
  expanding the 2026 card without validation.
- Research additional reliable sources for timely, up-to-date player-news
  feeds. Evaluate freshness, coverage, attribution and licensing requirements,
  stable player identity matching, cost, and failure behavior before selecting
  a provider. Any live feed must remain supplemental: locally cached context
  and the core draft workflow must continue to work when the feed is stale or
  unavailable.

## Technical Stack

- Live application: Next.js with TypeScript.
- Static modeling and data preparation: Python.
- Local persistence and recovery: SQLite.
- Shared/reporting integration: Google Sheets through an isolated synchronization adapter.
- Development environment: a dev container for reproducible setup and tooling.
- Draft-night runtime: a simple local launch path with minimal moving parts; it must not require the user to operate the dev container.

The TypeScript and Python sides should exchange versioned, validated artifacts or data contracts. Model training is static/offline work; live recalculation should use prepared outputs and fast deterministic logic appropriate for an auction clock.

## Success Benchmark

The product north star is the Rodman Renegades' probability of winning the
league championship. Playoff probability, expected optimal-lineup points,
points above league average, roster ceiling, resilience, and auction surplus
are diagnostic or intermediate measures; none replaces championship equity as
the final objective.

Before the fantasy schedule exists, use schedule-neutral championship equity:
average over balanced simulated schedules, weekly player outcomes, and the
confirmed four-team playoff structure. Keep three scenarios distinct:
drafted-roster/frozen, conservative replacement access, and (once Yahoo
transactions are available) historically calibrated active management. Do not
assume successful trades. During the season, condition the same framework on
actual rosters, standings, schedule, injuries, and remaining matchups.

Draft recommendations must remain construction-neutral. Do not encode or
select a named strategy such as concentrated spending, distributed spending,
or value-first. Generate legal attainable roster completions from the current
state and allow championship outcomes across price, projection, injury,
volatility, and replacement-access scenarios to determine the recommendation.
Named strategies are retrospective descriptions only.

The nomination workflow must present a state-specific price decision ladder
showing where the recommendation crosses strong pursue, lean pursue, neutral,
lean pass, and strong pass. Each threshold must explain which roster paths,
alternatives, or remaining-budget constraints caused the change. The complete
plain-language presentation contract is in `docs/product/draft-decision-guide.md`.
The live ladder evaluates a realistic market-aware price window rather than
extending to the mathematical maximum bid. Prices above the modeled market
range are progressively downgraded for overpay risk and lost roster
flexibility. Until the full championship simulator is calibrated for live
decisions, the interface shows scenario support—not the experimental
completion-path equity span—as its primary confidence signal.

The displayed price ladder is a one-way policy: after scenario scoring,
market-range adjustments, and budget-flexibility adjustments are composed, a
higher price may retain or worsen the prior recommendation but may never make
it more favorable. This invariant applies to the final recommendation shown to
the user, not only to its underlying scenario deltas.

Maintain a live secondary league-outlook view throughout the auction, ranking
all ten partial rosters by the same robust, schedule-neutral championship-
equity benchmark and realistic completion paths. Recalculate it after every
sale; it may live in a drawer, modal, or separate page rather than occupying the
primary nomination workspace. The Renegades' explicit draft target is first
place on this benchmark. Show uncertainty and treat materially overlapping
teams as close rather than manufacturing precision. At draft completion the
same view becomes the final draft scorecard. Decision efficiency and equity
regret remain separate supporting grades and must not alter the common league-
wide roster-strength benchmark.

The draft-night product succeeds operationally when a user can run an entire
real auction confidently from one local app: recover from a restart without
losing a completed action, continue through an internet outage, record a
nomination and final sale quickly, see correct budgets and rosters immediately,
and receive useful league-specific recommendations fast enough to influence the
next decision. Predictive success is evaluated separately through forward-only
historical calibration, uncertainty, and decision-policy replays.

Before draft night, verify this with a full replay or simulation of a historical draft, including forced network loss, interrupted Sheets synchronization, application restart, and restoration from persisted state. The final state and transaction history must remain correct, and the user must never need live bid-by-bid entry.

Any accepted change to a model, model input, source dataset, player-identity
mapping, league rule, or deterministic recommendation policy must rerun its
affected build and the isolated hardening suite before draft-night release. The
final evaluation uses deterministic seeds not used to develop the change,
reports recommendation-level differences and unintended effects, and does not
advance production pointers until human review. The repeatable procedure is in
`docs/operations/change-revalidation.md`.

## Order of Operations

1. Capture league rules, roster constraints, scoring, budgets, historical auction results, owner identities, and source-data contracts.
2. Build reproducible Python ingestion and cleaning pipelines; use FantasyPros as the primary projection backbone, nflverse/GSIS as the preferred player-identity backbone, enrich projections from source-isolated FFA and future datasets, and establish stable internal player and owner identifiers.
3. Create the evidence-selected JUGG sale-price model and the separate performance-value model, with historical market comparisons, evaluation metrics, uncertainty outputs, and versioned runtime artifacts.
4. Define the domain model and SQLite schema, including event history, state transitions, migrations, and recovery behavior.
5. Implement and test the deterministic live draft engine: nominations, completed sales, rosters, budgets, availability, inflation, scarcity, and recalculation.
6. Build the focused Next.js draft-night interface around the nominated-player
   workflow and fast final-sale entry, including unmistakably different preview,
   officially nominated, and sold visual states.
7. Add owner-tendency signals and expose their evidence and uncertainty in recommendations.
8. Add Google Sheets write-through, retry queues, status visibility, and reconciliation without weakening local authority.
9. Add proactive Copilot insights and grounded chat on top of stable local state and explainable model outputs.
10. Package a reproducible dev container and a separate simple local draft-night launch path.
11. Run historical replays, end-to-end draft simulations, offline and restart drills, performance checks, and a final draft-night readiness test.

## Non-Goals and Guardrails

- Do not require live bid-by-bid entry.
- Do not make Google Sheets, an AI service, or any other network service a prerequisite for core operation.
- Do not train heavy models or perform fragile data acquisition during the live draft.
- Do not allow recommendations to mutate authoritative draft state without an explicit user action.
- Do not hide model uncertainty or imply that owner behavior is deterministic.
