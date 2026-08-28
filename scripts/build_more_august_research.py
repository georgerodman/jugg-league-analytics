#!/usr/bin/env python3
"""Ingest the late-August research batch without refreshing AI summaries."""

import json
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BUILD="20260827T001500Z"
OUT=ROOT/"data/processed/fantasy_analysis"/BUILD
DB=ROOT/".local/renegade-draft-room.sqlite"
PLAYERS={name:player_id for player_id,name in sqlite3.connect(DB).execute("SELECT id,display_name FROM players")}

def t(name,label,summary,risks=(),price=None,sentiment=None,formats=("redraft","PPR")):
    player_id=PLAYERS.get(name)
    if not player_id:return None
    return {"player_id":player_id,"player_name":name,"label":label,"sentiment":sentiment or ("negative" if label in ("avoid","bust") else "positive"),"summary":summary,"rationale":summary,"risks":list(risks),"formats":list(formats),"price_condition":price,"assumptions":[]}

def source(source_id,title,author,url,content_type,summary,rows=()):
    return {"id":source_id,"title":title,"author":author,"url":url,"published_at":"2026-08-26","content_type":content_type,"summary":summary,"takeaways":[row for row in rows if row]}

SOURCES=[
 source("draftsharks:injury-predictor:2026-08-24","NFL Injuries - Draft Sharks Injury Predictor","Draft Sharks Team","https://www.draftsharks.com/injury-predictor","injury_model","Explains a premium machine-learning injury-risk model based on historical injuries and more than 1,000 variables. The public page exposes methodology but no player ratings, so it is retained as model context only."),
 source("fantasypros:staff:2026-injury-updates-aug26","Fantasy Football Injury Updates to Know for Your Drafts","FantasyPros Staff and Dr. Deepak Chona","https://www.fantasypros.com/2026/08/fantasy-football-injury-updates-to-know-for-your-drafts-2026/","injury_updates","Medical and fantasy interpretation of current injuries, recovery windows, reinjury risk, and price implications.",[
  t("Puka Nacua","target","Nacua's hip-flexor and sports-hernia concerns are improving, and the medical view does not support a meaningful injury downgrade.",["Modest reinjury risk and a separate possible suspension."],"Early second round"),
  t("Christian McCaffrey","target","McCaffrey's intermittent tightness is viewed as deliberate workload management, leaving him draftable in the back half of Round 1 with roster insurance.",["Age and soft-tissue history make him a conditional RB1."],"Back half of Round 1"),
  t("Ashton Jeanty","avoid","Jeanty's ankle injury could be a high-ankle sprain with a multi-week absence and efficiency ramp, prompting a meaningful downgrade.",["Severity remains uncertain and a low sprain would allow a much quicker return."],"Adjusted price; pair with backup"),
  t("Malik Nabers","target","Nabers' return to contact work supports a Week 1 return and early-second-round value.",["A four-week workload ramp and early efficiency dip remain plausible."],"Early Round 2"),
  t("Jeremiyah Love","avoid","Love's high-ankle sprain creates a possible six-week production dip and elevated reinjury risk, with one analyst out at current cost.",["A milder injury remains possible and another analyst accepts the risk."],"Current mid-round cost; add handcuff"),
  t("Emeka Egbuka","target","Egbuka's stable toe sprain is expected to permit a normal or mildly reduced Week 1, leaving analysts comfortable buying at cost.",["Tampa Bay's public injury messaging warrants caution."],"Current cost"),
  t("Luther Burden III","target","Burden's light jogging and teammate comments support a Week 1 return from his groin strain.",["Soft-tissue reinjury risk is real but described as modest."],"Current cost"),
  t("Tyler Warren","target","Warren's groin injury is viewed as short-term and insufficient to justify a ranking downgrade.",["A setback would change the low-risk outlook."],"Current cost"),
  t("Alec Pierce","avoid","Pierce's lingering ankle problem and required practice ramp create substantial early-season uncertainty, and both analysts moved off him at cost.",["A later surgical path could improve his midseason outlook."],"Avoid current cost"),
  t("Jonathon Brooks","target","Brooks' ACL recovery timeline, talent, and camp performance have moved one analyst ahead of Chuba Hubbard.",["Carolina can remain a committee and Brooks has two prior ACL tears."],"Rising ADP"),
  t("Chuba Hubbard","avoid","Hubbard's potentially significant hamstring injury threatens Week 1 and has shifted preference toward Jonathon Brooks.",["He has previously demonstrated top-12 production and the job remains unsettled."],"Current cost"),
  t("Jordyn Tyson","avoid","Tyson's recurring hamstring issue is expected to cost roughly two months plus a workload ramp, making him a redraft fade.",["The depressed price may create a dynasty buy-low opportunity."],"Avoid in redraft",formats=("redraft","dynasty")),
 ]),
 source("fantasypros:fanelli:2026-zero-wr-targets","13 Zero-WR Targets","Mike Fanelli","https://www.fantasypros.com/2026/08/13-zero-wr-targets-2026-fantasy-football/","strategy_targets","Thirteen receivers targeted from Round 5 through the final round in a PPR Zero-WR construction.",[
  t("Davante Adams","target","Adams can remain a strong Round 5 receiver even with touchdown regression because his 2025 scoring margin was substantial.",["Age, hamstring history, and touchdown regression."],"ADP 50.4 / WR22"),
  t("DJ Moore","target","Moore's move into Buffalo's lead-receiver vacancy creates a path to reproduce Stefon Diggs-level opportunity with Josh Allen.",["The new target hierarchy is not yet established."],"ADP 53.2 / WR23"),
  t("Rome Odunze","target","Odunze's elite early-2025 stretch and DJ Moore's departure support a top-12 ceiling if his target rate holds.",["Luther Burden and Colston Loveland still compete for work."],"ADP 61.6 / WR27"),
  t("Christian Watson","target","Watson's strong points-per-game production and Green Bay's vacated targets offer upside at a Round 6 price.",["Durability remains the defining risk."],"ADP 71.2 / WR30"),
  t("Marvin Harrison Jr.","target","Harrison is priced as a mid-round WR3 but could rebound into the top 12 under Arizona's new offensive staff.",["The breakout remains speculative after two disappointing years."],"ADP 75.4 / WR31"),
  t("Parker Washington","target","Washington's second-half WR11 pace, late-season surge, and camp reports support him as a Round 7-8 target.",["Jacksonville still has an ambiguous receiver hierarchy."],"ADP 75.6 / WR32"),
  t("Alec Pierce","target","Pierce's lead role, contract, efficiency, and touchdown production create top-20 upside if he reaches 100 targets.",["This recommendation conflicts with newer injury concerns."],"ADP 91.6 / WR37"),
  t("Wan'Dale Robinson","target","Robinson's continuity with Brian Daboll and consecutive 140-target seasons make him a Round 9-10 target.",["Carnell Tate will command substantial work."],"ADP 98.4 / WR39"),
  t("Chris Godwin Jr.","target","Godwin's health and camp form create a plausible bounce-back at WR40 cost.",["He missed 18 games over the prior two seasons."],"ADP 100.8 / WR40"),
  t("Jordan Addison","target","Addison's production with competent quarterback play supports a rebound with Kyler Murray.",["His 2025 output varied sharply by quarterback."],"ADP 108.6 / WR45"),
  t("KC Concepcion","sleeper","Concepcion's after-catch ability and fit in Todd Monken's offense make him the preferred late Cleveland receiver.",["Cleveland's offense and rookie competition remain uncertain."],"ADP 130.8 / WR50"),
  t("De'Zhaun Stribling","sleeper","Stribling's camp and preseason ascent gives him a path to become San Francisco's top receiver as a rookie.",["Veteran health and rotation can reduce his role."],"ADP 152.2 / WR57"),
  t("Ja'Kobi Lane","sleeper","Lane's camp performance and path to Baltimore's No. 2 target role make him a strong final-round pick.",["He remains behind Zay Flowers and competes with veterans."],"ADP 195.2 / WR62"),
 ]),
 source("fantasypros:tarracciano:2026-breakout-eight","8 Fantasy Football Breakout Players for 2026","Evan Tarracciano","https://www.fantasypros.com/2026/08/8-fantasy-football-breakout-players-for-2026/","breakouts","Eight players expected to exceed projections if their roles, health, and offensive environments cooperate.",[
  t("Justin Herbert","breakout","Healthy offensive tackles, strong receiving options, and Herbert's added rushing production create top-five quarterback upside.",["The case depends materially on improved line health."],"QB breakout cost"),
  t("Jared Goff","value","Goff's repeated top-eight finishes and elite passing volume make QB16 pricing overly pessimistic.",["He adds little rushing value."],"QB16"),
  t("Cam Skattebo","breakout","Skattebo is healthy, receiving-capable, and positioned as the clear lead back behind an improved Giants line.",["His physical style and major 2025 leg injury create durability risk."],"Lead-back cost"),
  t("Jadarian Price","breakout","Price's first-round capital and limited healthy competition create a strong early workload at RB26 cost.",["His receiving profile is less established and Zach Charbonnet may return."],"RB26"),
  t("Emeka Egbuka","breakout","Egbuka can become Tampa Bay's lead receiver with Mike Evans gone and carries favorable WR schedule support.",["Toe health and Chris Godwin remain relevant risks."],"WR breakout cost"),
  t("DJ Moore","breakout","Moore is expected to become Josh Allen's first read and primary deep threat after leaving Chicago.",["Camp chemistry must translate into regular-season target volume."],"WR breakout cost"),
  t("Isaiah Likely","breakout","Likely projects as the Giants' second read and red-zone mismatch after moving out of Mark Andrews' shadow.",["The role is projected from camp reports in a new offense."],"TE breakout cost"),
  t("Dallas Goedert","breakout","Goedert can offset touchdown regression with increased targets after A.J. Brown's departure and Makai Lemon's injury.",["His 11-touchdown 2025 season is unlikely to repeat."],"TE breakout cost"),
 ]),
 source("fantasydata:targets:2026-08-26","NFL Targets","FantasyData","https://fantasydata.com/nfl/targets","live_usage_table","A live targets dataset page. Registered as a volatile contextual source; its dynamic table is not converted into a static player opinion."),
 source("fantasydata:player-news:2026-08-26","Fantasy Football Player News","FantasyData","https://fantasydata.com/nfl/fantasy-football-player-news","live_player_news","A continuously changing player-news feed. Registered as a dated discovery source, not durable recommendation evidence."),
 source("fantasypros:johnson:2026-rb3-rb1-upside","6 RB3s With RB1 Potential","Ellis Bryn Johnson","https://www.fantasypros.com/2026/08/6-rb3s-with-rb1-potential-2026-fantasy-football/","upside_targets","Six backs with plausible top-12 outcomes that do not require an injury to a teammate.",[
  t("Bhayshul Tuten","breakout","Tuten's athleticism, first-team work, and open Jacksonville lead role create an every-down breakout path.",["Chris Rodriguez and passing-down specialist LeQuint Allen remain involved."],"RB23"),
  t("David Montgomery","value","Montgomery owns Houston's clearest lead-back path and can reach RB1 volume if the rebuilt line improves efficiency.",["His 2025 efficiency was poor and Houston's line improvement is unproven."],"RB24"),
  t("D'Andre Swift","value","Swift's durable top-24 history, 2025 lead role, and Chicago's potent offense give him a straightforward top-12 path.",["Kyle Monangai can regain a meaningful share after injury."],"RB3 price"),
  t("Tony Pollard","value","Pollard's dominant share and limited competition create volume-based RB1 upside if Tennessee's offense improves.",["He ranked only 30th in points per game with similar workload in 2025."],"RB3 price"),
  t("Chuba Hubbard","value","Hubbard has prior RB1 production and can return to that ceiling if he wins Carolina's productive backfield.",["A hamstring injury and Jonathon Brooks make this a true competition."],"RB3 price"),
  t("Jonathon Brooks","breakout","Brooks' talent and Hubbard's hamstring issue give him a rising chance to win Carolina's RB1-capable role.",["The backfield may stay a committee and Brooks has major knee history."],"Rising RB3 price"),
 ]),
]

def main():
    OUT.mkdir(parents=True,exist_ok=True);paths=[]
    for item in SOURCES:
        rows=item.pop("takeaways")
        artifact={"metadata":{"schema_version":2,"build_id":BUILD,"built_at":"2026-08-27T00:15:00Z","season":2026,"takeaway_count":len(rows)},"source":{"source_key":item["id"].split(":")[0],"season":2026,**item},"takeaways":rows}
        filename=item["id"].replace(":","_")+".json";(OUT/filename).write_text(json.dumps(artifact,indent=2)+"\n");paths.append(f"data/processed/fantasy_analysis/{BUILD}/{filename}")
    pointer=ROOT/"data/processed/fantasy_analysis/latest.json";data=json.loads(pointer.read_text());data["artifacts"]=[p for p in data["artifacts"] if f"/{BUILD}/" not in p]+paths;pointer.write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps({"sources":len(SOURCES),"takeaways":sum(len(json.loads((ROOT/p).read_text())["takeaways"]) for p in paths),"duplicate_skipped":"3 Fantasy Football Sleepers: Wide Receivers"}))

if __name__=="__main__":main()
