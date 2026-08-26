#!/usr/bin/env python3
"""Build reviewed 2026 research artifacts discovered during the independent source pass."""

import json
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD="20260826T230000Z"
OUT=ROOT/"data/processed/fantasy_analysis"/BUILD
DB=ROOT/".local/renegade-draft-room.sqlite"
PLAYERS={name:player_id for player_id,name in sqlite3.connect(DB).execute("SELECT id,display_name FROM players")}

def t(name,label,summary,risks,formats=("redraft","PPR"),price=None,assumptions=()):
    return {"player_id":PLAYERS[name],"player_name":name,"label":label,"sentiment":"negative" if label in ("avoid","bust") else "positive","summary":summary,"rationale":summary,"risks":list(risks),"formats":list(formats),"price_condition":price,"assumptions":list(assumptions)}

SOURCES=[
 {"id":"cbs:cummings:2026-deep-sleepers","title":"2026 Fantasy football deep sleepers: Tyler Shough and Tre Tucker are steals","author":"Heath Cummings","url":"https://secure-www.cbssports.com/fantasy/football/news/2026-fantasy-football-deep-sleepers-projections/","published_at":"2026-08-26","content_type":"deep_sleepers","summary":"Uses projection-versus-ADP gaps and plausible upside scenarios to identify players available outside the top 150.","takeaways":[
  t("Tyler Shough","sleeper","Cummings projects Shough near QB14 with substantial touchdown growth and sees additional second-half upside if Jordyn Tyson returns healthy.",["Touchdown improvement and Tyson's health are assumptions."],price="Round 13 / QB21"),
  t("Jalen Coker","value","Coker projects as Cummings' WR31 despite a Round 13 cost, supported by strong efficiency and more planned slot usage.",["Carolina still has competition for targets."],price="Rounds 10-13"),
  t("Malik Willis","sleeper","Willis' rushing projection gives him upside well beyond QB23 even if Miami remains a weak offense.",["Passing environment may be among the league's weakest."],price="Late QB2"),
  t("Dalton Schultz","value","Schultz is projected for another 100-plus targets and sits only a few points behind the TE9 projection despite a TE13 price.",["A top-eight outcome requires improved touchdown luck."],price="TE13 / ADP 173"),
  t("Tre Tucker","value","Tucker appears established as Las Vegas' WR1 and projects roughly 50 picks ahead of his ADP.",["The Raiders' passing environment remains a concern."],price="ADP 186"),
  t("Chris Bell","sleeper","If fully recovered from his ACL tear, Bell may be Miami's most talented receiver and a final-round upside play.",["ACL recovery and an unsettled offense."],price="Final round") ]},
 {"id":"cbs:eisenberg:2026-august-risers-fallers","title":"Jamey Eisenberg's mid-August risers and fallers","author":"Jamey Eisenberg","url":"https://www.cbssports.com/fantasy/football/news/fantasy-football-rankings-risers-fallers-jamey-eisenberg-august/","published_at":"2026-08-17","content_type":"risers_and_fallers","summary":"Updates rankings for preseason injuries, depth-chart movement, and changing roles.","takeaways":[
  t("Kyler Murray","target","Murray's confirmed Minnesota starting job, Kevin O'Connell, strong weapons, and rushing history create top-12 upside.",["His ADP may rise quickly."],price="Round 12"),
  t("Jordan Mason","target","Mason may be taking Minnesota's lead job and has produced efficiently when given double-digit carries.",["Limited receiving work lowers his floor."],price="Round 7"),
  t("KC Concepcion","sleeper","Cleveland is designing touches for Concepcion, making him a possible weekly three-receiver-league starter despite poor quarterback play.",["Cleveland's quarterback situation may cap consistency."],price="Rounds 9-11"),
  t("De'Zhaun Stribling","sleeper","Strong camp and preseason usage inside and outside give Stribling a path into San Francisco's depleted receiver rotation.",["Veterans ahead of him missed the evaluated game."],price="Round 9"),
  t("MarShawn Lloyd","sleeper","Lloyd is tracking as Green Bay's RB2 and could become an RB2 if Josh Jacobs misses time.",["Lloyd has played only one NFL game because of injuries."],price="Round 10"),
  t("Jonah Coleman","sleeper","Coleman is Denver's RB3 but has contingent upside behind injury-prone veterans and could earn designed work.",["He may open the season third on the depth chart."],price="Round 10"),
  t("Christian McCaffrey","avoid","A vague camp injury, age 30, and 450 touches make McCaffrey too risky near pick six.",["San Francisco has downplayed the current tightness."],price="Top six"),
  t("Jeremiyah Love","avoid","A high-ankle sprain, difficult schedule, and committee risk move Love from Round 2 into Round 3.",["The recommendation could improve if he returns fully before Week 1."],price="Avoid Round 2; consider Round 3"),
  t("Terry McLaurin","avoid","Stefon Diggs' arrival creates meaningful target competition and makes McLaurin risky at WR21 cost.",["McLaurin retains the higher individual ceiling."],price="WR21") ]},
 {"id":"nfl:okada:2026-late-round-sleepers","title":"2026 NFL fantasy football: Six late-round sleepers to target","author":"Matt Okada","url":"https://www.nfl.com/news/2026-nfl-fantasy-football-six-late-round-sleepers-to-target","published_at":"2026-08-12","content_type":"late_round_sleepers","summary":"Identifies six mostly double-digit-round targets using role, efficiency, and ESPN ADP.","takeaways":[
  t("Stefon Diggs","sleeper","Diggs' 2025 efficiency and new role as Washington's 1B make him a potential inexpensive WR2.",["Age and target competition with Terry McLaurin."],price="Rounds 9-10"),
  t("Chris Rodriguez Jr.","sleeper","Rodriguez has strong tackle-breaking metrics, comparable camp reps, and a plausible red-zone advantage over Bhayshul Tuten.",["Jacksonville may still favor Tuten or use a committee."],price="Round 10"),
  t("Dalton Kincaid","sleeper","Kincaid is a late tight-end target with a path to a larger Buffalo receiving role.",["He has yet to consistently convert opportunity into elite production."],price="Round 11 or later") ]},
 {"id":"nfl:okada:2026-breakouts","title":"2026 NFL fantasy football: Breakout candidates at QB, RB, WR and TE","author":"Matt Okada","url":"https://www.nfl.com/news/2026-nfl-fantasy-football-breakout-candidates-at-qb-rb-wr-and-te","published_at":"2026-08-07","content_type":"breakouts","summary":"Uses Next Gen Stats, role changes, and ESPN ADP to identify 14 breakout candidates in PPR formats.","takeaways":[
  t("Jaxson Dart","breakout","Dart already produced QB4-level scoring in his starts and regains key weapons behind an improved line.",["Concussion exposure and continued development as a passer."],assumptions=["Malik Nabers and Cam Skattebo return effectively."]),
  t("Cam Ward","breakout","Ward improved markedly after the 2025 bye and now has a much stronger receiver group.",["The offense still depends on a substantial second-year leap."]),
  t("Cam Skattebo","breakout","Skattebo produced like an elite back when healthy and now runs behind an improved, Harbaugh-shaped offense.",["Violent style, prior injury, and Tyrone Tracy's presence."]),
  t("Jordan Mason","breakout","League-leading missed-tackle and explosive-run rates create major upside as Aaron Jones declines.",["Receiving work and exact backfield split remain uncertain."]),
  t("Jonathon Brooks","breakout","Brooks' pedigree and late cost create upside if he becomes Carolina's needed second offensive playmaker.",["Two ACL tears and uncertain return of explosiveness."]),
  t("Quinshon Judkins","breakout","A rebuilt Cleveland line and Judkins' three-down profile create an elite ceiling if the offense stabilizes.",["Cleveland's quarterback and overall offensive quality."],assumptions=["The rebuilt line improves materially."]),
  t("Parker Washington","breakout","Washington's late-2025 pace and elite target rate with Jacksonville's starters suggest he can challenge for the team lead.",["Jacksonville's receiver room is crowded."]),
  t("Zay Flowers","breakout","Elite yards per route run plus potential touchdown growth could lift Flowers into the true WR1 tier.",["The breakout depends on improved scoring and weekly consistency."]),
  t("Tetairoa McMillan","breakout","McMillan's rookie production, likely target floor, and Bryce Young's upward trajectory support high-end upside.",["His ceiling depends on continued quarterback improvement."]),
  t("Josh Downs","breakout","Elite target and catch rates plus Michael Pittman's departure point to a major increase in routes and volume.",["The case is more valuable in reception-heavy formats."],formats=("redraft","PPR")) ]},
 {"id":"fantasypros:staff:2026-round-values","title":"Best Fantasy Football Draft Values in Every Round (2026)","author":"FantasyPros Staff","url":"https://www.fantasypros.com/2026/07/best-fantasy-football-draft-values-in-every-round-2026/","published_at":"2026-07","content_type":"round_values","summary":"Selects the best value in each round of a 12-team, one-quarterback PPR draft.","takeaways":[
  t("James Cook III","value","Cook's three-year rushing growth and consecutive 16-point PPR seasons make him a strong late-first value.",["First-round acquisition cost."],price="Round 1 / ADP 10.8"),
  t("Chase Brown","value","Brown has consecutive top-10-caliber seasons, stable featured usage, and a high-scoring offense.",["Requires another efficient, touchdown-heavy season."],price="Round 2 / ADP 19.8"),
  t("Rashee Rice","value","Rice's on-field production supports a third-round value if legal, suspension, and knee issues clear.",["Possible suspension, knee recovery, and off-field risk."],price="Round 3 / ADP 26.3"),
  t("Cam Skattebo","value","Skattebo's healthy 2025 stretch showed RB1 production at a fourth-round price.",["Recovery from a major ankle injury."],price="Round 4 / ADP 44.3"),
  t("DJ Moore","value","Moore gains Josh Allen and a path to become Buffalo's first true go-to receiver since Stefon Diggs.",["Role projection in a new offense."],price="Round 5 / ADP 56.5"),
  t("Rome Odunze","value","Odunze's hot 2025 start and DJ Moore's departure create a path to top-12 production.",["Luther Burden and Colston Loveland still compete for targets."],price="Round 6 / ADP 61.8"),
  t("Tucker Kraft","value","Kraft's pre-injury TE1 scoring rate and Green Bay's vacated targets support an elite ceiling.",["ACL recovery must hold through Week 1."],price="Round 7 / ADP 80.3") ]},
 {"id":"nfl:kownack:2026-riskiest","title":"2026 NFL fantasy football: 7 riskiest players to draft","author":"Bobby Kownack","url":"https://www.nfl.com/news/2026-nfl-fantasy-football-seven-riskiest-players-to-draft","published_at":"2026-08-04","content_type":"riskiest_players","summary":"Flags premium-cost players whose workload, age, injury, role, or situation creates unusually wide downside.","takeaways":[
  t("Christian McCaffrey","avoid","McCaffrey's 413 touches, declining rushing efficiency, and age-30 season make another first-round investment unusually fragile.",["Receiving volume still preserves an elite outcome."],price="Round 1 / RB3"),
  t("Jeremiyah Love","avoid","Love's talent is offset by a crowded backfield and little incentive for Arizona to give a rookie workhorse usage.",["Preseason performance could move the role."],price="Premium rookie cost"),
  t("Rashee Rice","avoid","Rice's production is strong, but legal, suspension, knee, and role uncertainty create excessive risk at the Round 2/3 turn.",["He can still be Kansas City's top target when active."],price="Round 2/3 turn"),
  t("Jaxson Dart","avoid","Dart has elite rushing upside but carries concussion, passing-development, Nabers-health, and coaching risks at QB9 cost.",["A safer rushing approach could lower his fantasy ceiling."],price="Round 7/8 / QB9"),
  t("George Kittle","avoid","Kittle is appealing late but becomes an avoid if Achilles optimism pushes a 33-year-old tight end too far up boards.",["He could return for Week 1 and retain an elite connection with Brock Purdy."],price="Avoid if price rises materially above Round 9") ]}
]

def main():
    OUT.mkdir(parents=True,exist_ok=True); paths=[]
    for source in SOURCES:
        takeaways=source.pop("takeaways")
        artifact={"metadata":{"schema_version":2,"build_id":BUILD,"built_at":"2026-08-26T23:00:00Z","season":2026,"takeaway_count":len(takeaways)},"source":{"source_key":source["id"].split(":")[0],"season":2026,**source},"takeaways":takeaways}
        filename=source["id"].replace(":","_")+".json";(OUT/filename).write_text(json.dumps(artifact,indent=2)+"\n");paths.append(f"data/processed/fantasy_analysis/{BUILD}/{filename}")
    pointer=ROOT/"data/processed/fantasy_analysis/latest.json";data=json.loads(pointer.read_text());data["artifacts"]=[p for p in data["artifacts"] if f"/{BUILD}/" not in p]+paths;pointer.write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps({"sources":len(SOURCES),"takeaways":sum(len(json.loads((ROOT/p).read_text())["takeaways"]) for p in paths)}))

if __name__=="__main__":main()
