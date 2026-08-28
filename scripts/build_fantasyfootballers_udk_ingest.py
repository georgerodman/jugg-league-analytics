#!/usr/bin/env python3
"""Ingest the supplied 2026 Fantasy Footballers/UDK research without refreshing summaries."""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = "20260827T223000Z"
BUILT_AT = "2026-08-27T22:30:00Z"
OUT = ROOT / "data/processed/fantasy_analysis" / BUILD
CONTEXT_OUT = ROOT / "data/processed/fantasy_context" / BUILD
PLAYERS = {name: pid for pid, name in sqlite3.connect(ROOT / ".local/renegade-draft-room.sqlite").execute("SELECT id, display_name FROM players")}
BASE = "https://www.thefantasyfootballers.com"


def take(name, label, summary, risk, price=None, sentiment=None):
    if name not in PLAYERS:
        raise ValueError(f"Unknown player: {name}")
    return {"player_id": PLAYERS[name], "player_name": name, "label": label,
            "sentiment": sentiment or ("negative" if label in ("avoid", "bust") else "positive"),
            "summary": summary, "rationale": summary, "risks": [risk],
            "formats": ["redraft"], "price_condition": price, "assumptions": []}


def src(sid, title, author, url, kind, summary, rows, published_at="2026-08-27"):
    return {"id": sid, "source_key": "fantasy_footballers", "title": title, "author": author,
            "url": url, "published_at": published_at, "content_type": kind,
            "summary": summary, "takeaways": rows}


SLEEPERS = [
    take("Malik Willis", "sleeper", "Elite rushing upside makes Willis an appealing late quarterback with QB1 weeks available.", "Miami's passing ceiling and his starting security remain uncertain.", "ADP 17.02"),
    take("Tyler Shough", "sleeper", "A strong starting pace, favorable schedule and improving weapons create late QB1 upside.", "The breakout case rests on a limited NFL sample.", "ADP 16.11"),
    take("Rico Dowdle", "sleeper", "An unsettled Pittsburgh backfield gives Dowdle a path to a useful lead role at a modest price.", "Jaylen Warren can retain meaningful work.", "ADP 7.11"),
    take("Jonathon Brooks", "sleeper", "Receiving ability and an open path past Chuba Hubbard create inexpensive upside.", "His health and post-injury workload remain uncertain.", "ADP 8.05"),
    take("Blake Corum", "sleeper", "Corum narrowed the gap with Kyren Williams and offers both standalone work and premium contingency value.", "The Rams can remain a committee while Williams is healthy.", "ADP 8.09"),
    take("Jacory Croskey-Merritt", "sleeper", "Early-down opportunity in a productive offense gives Croskey-Merritt an RB1 path at a late price.", "Rachaad White and a rookie can control passing-down work.", "ADP 9.03"),
    take("Jordan Mason", "sleeper", "Efficient early-down and goal-line work provides standalone value behind Aaron Jones.", "Jones is favored for passing downs and remains the starter.", "ADP 9.02"),
    take("Quentin Johnston", "sleeper", "Mike McDaniel's perimeter usage and Justin Herbert's arm create an inexpensive WR3 ceiling.", "Target competition and prior inconsistency lower the floor.", "ADP 9.10"),
    take("Josh Downs", "sleeper", "Vacated targets can turn Downs into an every-down receiver at a late price.", "The Indianapolis target hierarchy is still unsettled.", "ADP 9.12"),
    take("Parker Washington", "sleeper", "His strong late-2025 production offers lead-receiver upside despite a crowded Jacksonville room.", "Multiple capable receivers make his weekly share uncertain.", "ADP 6.12"),
    take("De'Zhaun Stribling", "sleeper", "Size, speed and a plausible early role make Stribling a worthwhile late rookie bet.", "His role depends partly on injuries ahead of him.", "ADP 11.05"),
    take("Isaiah Likely", "sleeper", "A featured Giants role and proven production without Mark Andrews create late tight-end upside.", "His new offense and target share are not yet established.", "ADP 10.04"),
    take("Chig Okonkwo", "sleeper", "Washington's thin receiving depth gives Okonkwo a path to become a primary target.", "Veteran receivers can keep him third in the pecking order.", "ADP 17.04"),
    take("Greg Dulcich", "sleeper", "Every-down athleticism offers deep-league upside in Miami's unsettled receiving group.", "The offense may not support a weekly top-12 tight end.", "ADP 21.03"),
]

BREAKOUTS = [
    take("Jaxson Dart", "breakout", "Dart's rushing production and John Harbaugh's arrival create a difference-making sophomore ceiling.", "His aggressive running style creates substantial injury risk.", "ADP 9.07"),
    take("Trevor Lawrence", "breakout", "A QB4 finish, strong late run and valuable rushing production support another leap in Liam Coen's offense.", "His 2025 rushing touchdowns may regress.", "ADP 9.01"),
    take("Omarion Hampton", "breakout", "A healthy line and Mike McDaniel's scheme set Hampton up for a true workhorse role.", "Keaton Mitchell can siphon explosive and receiving work.", "ADP 2.03"),
    take("Kenneth Walker III", "breakout", "Kansas City's large investment and empty depth chart create a path for the offense to run through Walker.", "His career workload and receiving volume have been inconsistent.", "ADP 2.06"),
    take("Bhayshul Tuten", "breakout", "Etienne's departure and Tuten's goal-line efficiency create RB1 upside in an attractive offense.", "Other backs can split power and receiving duties.", "ADP 5.12"),
    take("Christian Watson", "breakout", "Elite per-route production and reduced receiver competition give Watson a strong WR3-or-better ceiling.", "His injury history and Green Bay's spread offense remain concerns.", "ADP 6.08"),
    take("Carnell Tate", "breakout", "Fourth-overall draft capital and a sparse Tennessee depth chart create immediate alpha-receiver opportunity.", "The ceiling depends on Cam Ward making a meaningful leap.", "ADP 6.08"),
    take("Tetairoa McMillan", "breakout", "A 25% rookie target share and little new competition position McMillan for a classic Year 2 leap.", "Bryce Young and touchdown growth must cooperate.", "ADP 3.12"),
    take("Colston Loveland", "breakout", "A dominant late-season target surge and Caleb Williams' trust create elite tight-end upside.", "Chicago still has several strong target earners.", "ADP 4.08"),
    take("Harold Fannin Jr.", "breakout", "David Njoku's departure opens enough work for Fannin to build on a dominant late-season run.", "Cleveland's quarterback situation limits the floor.", "ADP 7.02"),
]

BUSTS = [
    take("Patrick Mahomes II", "bust", "A major knee recovery, limited receiver additions and reduced rushing make separation at quarterback unlikely.", "His talent and offense can still create an outlier passing season.", "ADP 10.03"),
    take("Jordan Love", "bust", "Low passing volume and limited rushing require an unsustainable touchdown spike for difference-making fantasy output.", "Efficiency preserves matchup-streaming appeal.", "ADP 14.12"),
    take("Jeremiyah Love", "bust", "A poor team environment and shared touches make the highly drafted rookie vulnerable to disappointment.", "Elite talent and draft capital can overwhelm the situation.", "ADP 3.02"),
    take("Chuba Hubbard", "bust", "Weak explosiveness, almost no goal-line work and Jonathon Brooks' rise threaten Hubbard's seventh-round cost.", "He may still open as Carolina's lead back.", "ADP 7.05"),
    take("RJ Harvey", "bust", "Touchdown regression, poor rushing efficiency and a crowded backfield make Harvey's price fragile.", "Denver's excellent line and offense preserve usable upside.", "ADP 7.08"),
    take("Malik Nabers", "bust", "ACL and meniscus recovery plus a spring follow-up procedure make an early premium price difficult to accept.", "A late-season return to elite form remains possible.", "ADP 3.06"),
    take("DJ Moore", "bust", "Age, career-low efficiency and Buffalo's distributed passing game make the Josh Allen premium risky.", "A clear top-receiver role can still unlock a rebound.", "ADP 5.08"),
    take("Courtland Sutton", "bust", "Jaylen Waddle's arrival, age and likely volume loss can turn Sutton into a touchdown-dependent option.", "He has posted consecutive WR13 finishes.", "ADP 7.11"),
    take("Oronde Gadsden II", "bust", "New tight-end competition and inconsistent first-team camp work make Gadsden an avoid at his current cost.", "His rookie peak still demonstrates meaningful receiving upside.", "ADP 13.03"),
    take("Dalton Kincaid", "bust", "Low target volume, added underneath competition and possible snap management make similar production available later.", "Josh Allen keeps his touchdown ceiling alive.", "ADP 8.08"),
    take("Jake Ferguson", "bust", "A weak second half and third-place target role leave Ferguson overly dependent on touchdowns.", "Dallas' passing volume can still create spike weeks.", "ADP 10.01"),
]

VALUES = [
    take("Matthew Stafford", "value", "A double-digit-round price already accounts for touchdown regression in the league's highest-total offense.", "His MVP-level touchdown rate is unlikely to repeat.", "ADP 9.11"),
    take("Brock Purdy", "value", "Consistent touchdown production, some rushing floor and early high-total matchups make Purdy an overlooked QB2.", "His weekly ceiling can depend on game environment.", "ADP 11.02"),
    take("Dak Prescott", "value", "Reliable volume, heavy red-zone passing and a career-long top-12 track record make Prescott a strong late backstop.", "He offers less rushing upside than elite options.", "ADP 8.01"),
    take("Derrick Henry", "value", "A league-leading win projection and durable touchdown role make Henry attractive at a discounted second-round cost.", "Age and workload decline remain unavoidable risks.", "ADP 2.04"),
    take("Javonte Williams", "value", "A new extension and almost no backfield competition support another 300-opportunity RB1 season.", "Last season's touchdown total can regress.", "ADP 3.10"),
    take("Cam Skattebo", "value", "A likely three-down and goal-line role creates top-10 upside at an injury-discounted RB2 price.", "He is returning from a major leg injury.", "ADP 4.02"),
    take("D'Andre Swift", "value", "Career highs behind a strong line and no major new competition provide a stable RB2 floor.", "Kyle Monangai will retain a complementary role.", "ADP 5.01"),
    take("J.K. Dobbins", "value", "Denver re-signed Dobbins to lead carries behind an elite line, making his late starter price attractive.", "RJ Harvey can command passing-down work.", "ADP 8.01"),
    take("Brian Thomas Jr.", "value", "His every-down X role and strong two-receiver usage preserve rebound upside at a WR3 price.", "Jacksonville's crowded receiver room creates weekly uncertainty.", "ADP 6.12"),
    take("Emeka Egbuka", "value", "Mike Evans' departure leaves Egbuka positioned for a lead role and a possible Year 2 top-12 finish.", "His late-2025 efficiency collapse cannot be ignored.", "ADP 4.05"),
    take("Jaylen Waddle", "value", "Denver paid premium capital for Waddle, whose route efficiency and screen fit create easy-volume upside.", "Courtland Sutton and Denver's spread offense compete for volume.", "ADP 4.12"),
    take("Terry McLaurin", "value", "A healthy Jayden Daniels and shootout-friendly schedule make McLaurin's one-round discount attractive.", "Stefon Diggs adds legitimate target competition.", "ADP 5.05"),
    take("Brenton Strange", "value", "A 16% target share and expanded two-tight-end usage make Strange a cheap late streamer with growth potential.", "He has not yet established a weekly fantasy floor.", "ADP 14.02"),
    take("Sam LaPorta", "value", "A reduced price restores access to LaPorta's double-digit-touchdown ceiling in an elite offense.", "A crowded target tree and recent injuries add volatility.", "ADP 6.04"),
]

STAFF = [
    ("Chris Cash", "TreVeyon Henderson", "breakout", "Elite per-snap production and a proven three-down ceiling make Henderson attractive at an RB24 price.", "Rhamondre Stevenson can retain a large role."),
    ("Kurt Mullen", "Bhayshul Tuten", "breakout", "An ambiguous backfield and Liam Coen's offense give Tuten lead-back upside.", "Specialized teammates can cap high-value touches."),
    ("Maggie Thraen", "Jameson Williams", "breakout", "A WR9 finish despite poor conditions and a huge post-bye pace support another leap.", "Deep production remains naturally volatile."),
    ("Aaron Larson", "DJ Moore", "value", "Josh Allen, Joe Brady and a fifth-round price create a compelling rebound setup.", "Buffalo has rarely concentrated targets on one receiver."),
    ("Javier Manzanera", "Trevor Lawrence", "value", "A second-half QB1 run and continuity with Liam Coen make Lawrence underpriced.", "Rushing-touchdown regression can lower the finish."),
    ("Peter Kettering", "Jaylen Waddle", "value", "Denver's major trade investment, strong line and fast offense create favorable volume at a fourth-round cost.", "Courtland Sutton still commands targets."),
    ("Kemper Trull", "Luther Burden III", "breakout", "Elite YAC, route efficiency and separation create a breakout if volume rises.", "Health and target competition remain concerns."),
    ("Colton Williams", "Bo Nix", "value", "Consecutive QB7 finishes plus Jaylen Waddle make a QB14 price too cheap.", "Denver can remain balanced near the goal line."),
    ("Scott Freymond", "Parker Washington", "sleeper", "Strong late-season efficiency and a sixth-round price create useful upside.", "Jacksonville's receiver rotation is crowded."),
    ("Nate Henry", "Jameson Williams", "breakout", "Expanded routes, a quiet offseason and strong camp reports support another step forward.", "The profile still relies on explosive plays."),
    ("Parker Hagen", "Jacory Croskey-Merritt", "sleeper", "A likely feature role in a good offense offers meaningful ninth-round upside.", "Passing-game growth is not guaranteed."),
    ("Brooke Morgan", "Chig Okonkwo", "sleeper", "Career highs and Washington's open target tree create a low-cost breakout path.", "Two veteran receivers remain ahead of him."),
    ("Mike Manderson", "Ladd McConkey", "value", "Better line health, Mike McDaniel and vacated targets create a strong bounce-back case.", "Last season's pressure-driven decline may not fully reverse."),
    ("Jordan Pullett", "Justin Herbert", "breakout", "Mike McDaniel, healthy tackles and improved efficiency can restore difference-making quarterback production.", "The offense may remain balanced."),
    ("Paul Marnie", "D'Andre Swift", "value", "A strong line, career highs and a secure lead role offer RB1 ceiling at an RB3 price.", "Kyle Monangai will mix in."),
    ("Vernon Meighan", "Christian Watson", "breakout", "A major extension, explosive post-ACL form and vacated targets support a leap.", "His durability remains a central risk."),
    ("Brittney Foxworth", "Tyler Warren", "breakout", "Vacated targets and a minor groin concern position Warren to dominate Indianapolis volume.", "The groin issue and changing offense warrant monitoring."),
    ("Marvin Elequin", "Javonte Williams", "value", "Strong Dallas efficiency and a lead role in a high-EPA offense create RB1 upside at RB16 cost.", "Workload and touchdown repeatability are uncertain."),
    ("Julia Papworth", "Zay Flowers", "value", "A large extension, dominant team shares and weak competition make Flowers attractive at WR15.", "Baltimore's passing volume can fluctuate."),
    ("Matthew Betz", "Tee Higgins", "value", "Cincinnati's offense, favorable schedule and concentrated targets create discounted upside.", "Health and Ja'Marr Chase cap the ceiling."),
    ("Kyle Borgognoni", "KC Concepcion", "sleeper", "First-round capital and a complete college profile create PPR upside at WR46 cost.", "Cleveland's quarterback play lowers the floor."),
]

SOURCES = [
    src("fantasyfootballers:udk:2026-sleepers", "2026 UDK Expert List: Sleepers", "Fantasy Footballers", BASE + "/2026-ultimate-draft-kit/udk-expert-lists-sleepers/", "sleepers", "Fourteen late-round sleeper selections with ADP context.", SLEEPERS),
    src("fantasyfootballers:udk:2026-breakouts", "2026 UDK Expert List: Breakouts", "Fantasy Footballers", BASE + "/2026-ultimate-draft-kit/udk-expert-lists-breakouts/", "breakouts", "Ten players with role, efficiency or second-year breakout cases.", BREAKOUTS),
    src("fantasyfootballers:udk:2026-busts", "2026 UDK Expert List: Busts", "Fantasy Footballers", BASE + "/2026-ultimate-draft-kit/udk-expert-lists-busts/", "busts", "Eleven price-sensitive fades covering role, injury and regression risk.", BUSTS),
    src("fantasyfootballers:udk:2026-values", "2026 UDK Expert List: Values", "Fantasy Footballers", BASE + "/2026-ultimate-draft-kit/udk-expert-lists-values/", "values", "Fourteen players whose cost trails their projected role or ceiling.", VALUES),
    src("fantasyfootballers:2026-rashee-rice-for", "Fantasy Court: The Case for Rashee Rice", "Fantasy Footballers", BASE + "/analysis/fantasy-court-the-case-for-rashee-rice-in-2026-fantasy-football/", "player_case", "The positive side of a deliberately two-sided player debate.", [take("Rashee Rice", "target", "Prior WR1 production, repeatable target share and red-zone opportunity support a strong ceiling.", "Availability and crowded Kansas City competition remain meaningful.")], "2026-08-23"),
    src("fantasyfootballers:2026-rashee-rice-against", "Fantasy Court: The Case against Rashee Rice", "Fantasy Footballers", BASE + "/analysis/fantasy-court-the-case-against-rashee-rice-in-2026-fantasy-football/", "player_case", "The negative side of a deliberately two-sided player debate.", [take("Rashee Rice", "avoid", "Availability risk, an elevated price and a changing Kansas City offense make Rice difficult to trust.", "His proven target-earning ability can still overcome those concerns.")], "2026-08-23"),
]

for author, name, label, summary, risk in STAFF:
    SOURCES.append(src("fantasyfootballers:staff-my-guys:2026:" + author.lower().replace(" ", "-"), "Fantasy Footballers Writing Staff My Guys for 2026", author, BASE + "/analysis/the-fantasy-footballers-writing-staff-my-guys-for-2026/", "staff_my_guys", "One contributor's 2026 My Guy selection.", [take(name, label, summary, risk)]))

MAIN = {
    "Jason Moore": [
        take("Garrett Wilson", "value", "A proven 30% target share and fourth-round WR20 price create substantial upside.", "Quarterback quality remains uncertain."),
        take("Carnell Tate", "breakout", "Fourth-overall capital and a likely hyper-targeted WR1 role make Tate attractive in Round 6.", "Rookie receivers carry a wide outcome range."),
        take("Omarion Hampton", "breakout", "Workhorse usage, goal-line control and Mike McDaniel's outside-zone system support an RB1 ceiling.", "Keaton Mitchell can reduce the workload."),
    ],
    "Mike Wright": [
        take("Christian Watson", "value", "Elite post-ACL route metrics and a cleared receiver room make Watson underpriced.", "His injury history remains significant."),
        take("Colston Loveland", "breakout", "Dominant late-season efficiency and a featured Ben Johnson role create elite tight-end upside.", "Chicago has several target earners."),
        take("Kenneth Walker III", "breakout", "Kansas City's investment, explosive rushing and major vacated red-zone work create a huge ceiling.", "He has not handled a full workhorse season."),
    ],
    "Andy Holloway": [
        take("Ladd McConkey", "value", "Elite early-career production and Mike McDaniel's motion offense make a Round 4-5 discount attractive.", "Health and target redistribution add uncertainty."),
        take("De'Zhaun Stribling", "sleeper", "Draft capital, size, speed and a path to snaps make Stribling a strong late rookie bet.", "His starting role is not guaranteed."),
        take("Caleb Williams", "value", "QB7 production, rushing upside, a strong line and elite weapons make Williams a seventh-round value.", "Pressure handling and consistency still need improvement."),
    ],
}
for author, rows in MAIN.items():
    SOURCES.append(src("fantasyfootballers:ballers-my-guys:2026:" + author.lower().replace(" ", "-"), "The Fantasy Footballers My Guys for 2026", author, BASE + "/analysis/the-fantasy-footballers-my-guys-for-2026/", "my_guys", "Three 2026 conviction picks from one host.", rows))

CONTEXT_SOURCES = [
    ("coaching_changes", "/2026-ultimate-draft-kit/udk-coaching-changes/", "Team-level head-coach and offensive-coordinator changes with fantasy implications."),
    ("rookie_reports", "/2026-ultimate-draft-kit/udk-rookie-report/", "Scouting and projected-role reports for the 2026 rookie class."),
    ("free_agency_review", "/2026-ultimate-draft-kit/udk-free-agency-review/", "Player movement and team-fit context across quarterback, running back, receiver and tight end."),
    ("injury_report", "/2026-ultimate-draft-kit/udk-injury-report/", "Dated recovery context for major quarterback, running back, receiver and tight-end injuries."),
    ("target_share", "/2026-ultimate-draft-kit/udk-target-share/", "2025 team target and completion shares by RB, WR and TE."),
    ("market_share_rb", "/2026-ultimate-draft-kit/udk-market-share/?position=RB", "2025 running-back team rushing, receiving and fantasy-point market shares."),
    ("market_share_wr", "/2026-ultimate-draft-kit/udk-market-share/?position=WR", "2025 wide-receiver target, reception, yardage, touchdown and fantasy-point market shares."),
    ("market_share_te", "/2026-ultimate-draft-kit/udk-market-share/?position=TE", "2025 tight-end target, reception, yardage, touchdown and fantasy-point market shares."),
    ("red_zone_passing", "/2026-ultimate-draft-kit/udk-red-zone/?position=passing", "2025 passing usage and production inside the 20 and 10."),
    ("red_zone_rushing", "/2026-ultimate-draft-kit/udk-red-zone/?position=rushing", "2025 rushing usage and production inside the 20 and 10."),
    ("red_zone_receiving", "/2026-ultimate-draft-kit/udk-red-zone/?position=receiving", "2025 receiving usage and production inside the 20 and 10."),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = []
    for item in SOURCES:
        artifact = {"metadata": {"schema_version": 2, "build_id": BUILD, "built_at": BUILT_AT, "season": 2026, "takeaway_count": len(item["takeaways"])},
                    "source": {k: item[k] for k in ("id", "source_key", "title", "author", "url", "published_at", "content_type", "summary")} | {"season": 2026},
                    "takeaways": item["takeaways"]}
        filename = item["id"].replace(":", "_") + ".json"
        (OUT / filename).write_text(json.dumps(artifact, indent=2) + "\n")
        paths.append(str((OUT / filename).relative_to(ROOT)))
    pointer_path = ROOT / "data/processed/fantasy_analysis/latest.json"
    pointer = json.loads(pointer_path.read_text())
    pointer["artifacts"] = [p for p in pointer["artifacts"] if f"/{BUILD}/" not in p] + paths
    pointer_path.write_text(json.dumps(pointer, indent=2) + "\n")

    old_pointer = json.loads((ROOT / "data/processed/fantasy_context/latest.json").read_text())
    context = json.loads((ROOT / old_pointer["artifact"]).read_text())
    context["metadata"] = {"schema_version": 2, "build_id": BUILD, "built_at": BUILT_AT}
    context["datasets"]["fantasyfootballers_udk_2026"] = {
        "season": 2026, "retrieved_at": BUILT_AT, "classification_effect": "context_only",
        "notes": "Subscription pages were reviewed through the operator's authenticated browser. Query-string position views are one underlying source and are deduplicated here.",
        "sources": [{"id": key, "url": BASE + path, "summary": summary} for key, path, summary in CONTEXT_SOURCES],
    }
    CONTEXT_OUT.mkdir(parents=True, exist_ok=True)
    context_path = CONTEXT_OUT / "fantasyfootballers_udk_context.json"
    context_path.write_text(json.dumps(context, indent=2) + "\n")
    (ROOT / "data/processed/fantasy_context/latest.json").write_text(json.dumps({"schema_version": 2, "artifact": str(context_path.relative_to(ROOT))}, indent=2) + "\n")
    print(json.dumps({"opinion_sources": len(SOURCES), "takeaways": sum(len(x["takeaways"]) for x in SOURCES), "context_sources": len(CONTEXT_SOURCES)}))


if __name__ == "__main__":
    main()
