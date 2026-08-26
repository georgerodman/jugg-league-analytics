#!/usr/bin/env python3
"""Build source-attributed ESPN fantasy research artifacts for the 2026 draft."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_ID = "20260826T210000Z"
OUT = ROOT / "data/processed/fantasy_analysis" / BUILD_ID

PLAYERS = {
    row.split("|")[1]: row.split("|")[0]
    for row in """nfl:gsis:00-0036919|Kenny Gainwell
nfl:gsis:00-0039738|Blake Corum
nfl:gsis:00-0039344|Jonathon Brooks
nfl:gsis:00-0040236|Kyle Monangai
nfl:gsis:00-0037746|Brian Robinson Jr.
nfl:gsis:00-0038555|Tank Bigsby
nfl:gsis:00-0039165|Zach Charbonnet
nfl:gsis:00-0040242|Jacory Croskey-Merritt
nfl:gsis:00-0038611|Chris Rodriguez Jr.
nfl:gsis:00-0040583|Woody Marks
nfl:gsis:00-0039384|Tyrone Tracy Jr.
nfl:gsis:00-0036442|Joe Burrow
nfl:gsis:00-0033280|Christian McCaffrey
nfl:gsis:00-0039040|De'Von Achane
nfl:gsis:00-0039361|Bucky Irving
nfl:gsis:00-0039337|Malik Nabers
nfl:gsis:00-0031381|Davante Adams
nfl:gsis:00-0034351|Dallas Goedert
nfl:gsis:00-0040743|Tyler Shough
nfl:gsis:00-0039163|C.J. Stroud
nfl:gsis:00-0041032|Kenyon Sadiq
nfl:gsis:00-0040676|Cam Ward
nfl:gsis:00-0031408|Mike Evans
nfl:gsis:00-0040663|Harold Fannin Jr.
nfl:gsis:00-0026498|Matthew Stafford
nfl:gsis:00-0035700|Josh Jacobs
nfl:gsis:00-0040666|Omarion Hampton
nfl:gsis:00-0040129|Emeka Egbuka
nfl:gsis:00-0041027|Jeremiyah Love
nfl:gsis:00-0040719|Bhayshul Tuten
nfl:gsis:00-0040735|Luther Burden III
nfl:gsis:00-0041512|Jadarian Price
nfl:gsis:00-0040122|Ashton Jeanty
nfl:gsis:00-0040691|Jaxson Dart
nfl:gsis:00-0039851|Drake Maye
nfl:gsis:00-0039910|Jayden Daniels
nfl:gsis:00-0034857|Josh Allen
nfl:gsis:00-0035710|Daniel Jones
nfl:gsis:00-0036264|Jordan Love
nfl:gsis:00-0039067|Rashee Rice
nfl:gsis:00-0035676|A.J. Brown
nfl:gsis:00-0039849|Marvin Harrison Jr.
nfl:gsis:00-0036970|Kyle Pitts Sr.
nfl:gsis:00-0037248|James Cook III
nfl:gsis:00-0032764|Derrick Henry
nfl:gsis:00-0038597|Chase Brown
nfl:gsis:00-0036997|Javonte Williams
nfl:gsis:00-0035685|David Montgomery
nfl:gsis:00-0036158|J.K. Dobbins
nfl:gsis:00-0037256|Rachaad White
nfl:gsis:00-0033906|Alvin Kamara
nfl:gsis:00-0037834|Brock Purdy
nfl:gsis:00-0033873|Patrick Mahomes II
nfl:gsis:00-0033106|Jared Goff
nfl:gsis:00-0035228|Kyler Murray
nfl:gsis:00-0038128|Malik Willis
nfl:gsis:00-0036322|Justin Jefferson
nfl:gsis:00-0038994|Jordan Addison
nfl:gsis:00-0039064|Zay Flowers
nfl:gsis:00-0037240|Jameson Williams
nfl:gsis:00-0038997|Josh Downs
nfl:gsis:00-0038117|Wan'Dale Robinson
nfl:gsis:00-0039880|Malik Washington
nfl:gsis:00-0038996|Tucker Kraft
nfl:gsis:00-0034753|Mark Andrews
nfl:gsis:00-0035229|T.J. Hockenson
nfl:gsis:00-0038933|Dalton Kincaid
nfl:gsis:00-0033090|Hunter Henry
nfl:gsis:00-0033077|Dak Prescott
nfl:gsis:00-0038120|Breece Hall
nfl:gsis:00-0040715|Cam Skattebo
nfl:gsis:00-0037740|Garrett Wilson
nfl:gsis:00-0035659|Terry McLaurin
nfl:gsis:00-0036252|Michael Pittman Jr.
nfl:gsis:00-0034960|Jakobi Meyers
nfl:gsis:00-0033921|Chris Godwin Jr.
nfl:gsis:00-0039491|Jalen Coker
nfl:gsis:00-0041561|Carson Beck
nfl:gsis:00-0037252|Greg Dulcich
nfl:gsis:00-0040727|Tre' Harris
nfl:gsis:00-0040870|Ja'Kobi Lane
nfl:gsis:00-0039811|MarShawn Lloyd
nfl:gsis:00-0040886|Nicholas Singleton
nfl:gsis:00-0041496|Jonah Coleman
nfl:gsis:00-0040878|Mike Washington Jr.
nfl:gsis:00-0041013|Emmett Johnson
nfl:gsis:00-0041523|Caleb Douglas
nfl:gsis:00-0041525|Chris Bell
nfl:gsis:00-0041035|De'Zhaun Stribling
nfl:gsis:00-0041052|Kaelon Black
nfl:gsis:00-0041044|Zachariah Branch
nfl:gsis:00-0041040|Antonio Williams
nfl:gsis:00-0034827|DJ Moore
nfl:gsis:00-0039338|Brock Bowers
nfl:gsis:00-0038134|Kenneth Walker III
nfl:gsis:00-0037809|Chig Okonkwo""".splitlines()
}

def t(name, label, summary, risks=None, sentiment=None):
    return {
        "player_id": PLAYERS[name], "player_name": name, "label": label,
        "sentiment": sentiment or ("negative" if label in ("avoid", "bust") else "positive"),
        "summary": summary, "rationale": summary,
        "risks": risks or ["Role, health, team context, and draft price can change before the season."],
    }

SOURCES = [
  ("espn:moody:2026-rb-insurance", "Fantasy football insurance RB rankings: Which backups are must-drafts?", "Eric Moody", "2026-08-04", "running_back_insurance", "Ranks backup running backs by stand-alone usability and the upside they would gain if the starter missed time.", [
    t("Kenny Gainwell","value","Moody ranks Gainwell first: usable in deeper leagues now and an RB1 candidate if Bucky Irving misses time."),
    t("Blake Corum","value","Corum projects for roughly a 40% share and flex value, with RB1 upside if Kyren Williams is out."),
    t("Jonathon Brooks","value","Brooks offers second-half and receiving upside but requires patience after two ACL tears.",["Two ACL tears and a potentially cautious early-season workload."]),
    t("Kyle Monangai","value","Monangai has flex appeal behind D'Andre Swift and could become an RB1 in Chicago's favorable line environment."),
    t("Brian Robinson Jr.","value","Robinson lacks a large receiving role but would carry RB1 upside if Bijan Robinson missed time."),
    t("Tank Bigsby","value","Bigsby has limited stand-alone value but projects as an RB2 if Saquon Barkley is unavailable."),
    t("Zach Charbonnet","value","Charbonnet could return to a committee role and touchdown work, though his ACL recovery may extend into October.",["ACL rehabilitation and an uncertain return date."]),
    t("Jacory Croskey-Merritt","value","Croskey-Merritt leads an unsettled Washington committee projection but carries workload uncertainty."),
    t("Chris Rodriguez Jr.","value","Rodriguez is a late early-down target in Jacksonville, with limited receiving upside."),
    t("Woody Marks","value","Marks is a Year 2 contingency bet who could become an RB2 if David Montgomery misses time."),
    t("Tyrone Tracy Jr.","value","Tracy has dual-threat bench value and RB2 upside if Cam Skattebo is unavailable.")]),
  ("espn:loza:2026-big-name-avoids", "You can have 'em: Six big-name players I'll be passing on in drafts", "Liz Loza", "2026-08-06", "players_to_avoid", "Identifies six expensive veterans or stars whose injury, efficiency, role, or touchdown risks outweigh their current draft prices.", [
    t("Joe Burrow","avoid","Loza is passing at QB5 cost because Cincinnati's line, Burrow's limited rushing, and his injury history weaken the value."),
    t("Christian McCaffrey","avoid","A 413-touch season, age-30 curve, efficiency concerns, and first-round cost make McCaffrey too fragile at price."),
    t("De'Von Achane","avoid","Miami's changed quarterback, receivers, and coaching environment could reduce Achane's receiving efficiency and space."),
    t("Malik Nabers","avoid","ACL and meniscus recovery plus limited work with Jaxson Dart make Nabers risky at a third-round price."),
    t("Davante Adams","avoid","Adams relied heavily on end-zone production in 2025, creating touchdown-regression risk at age 33."),
    t("Dallas Goedert","avoid","Goedert's unusually high catch-to-touchdown rate and declining yards per catch make a repeat unlikely.")]),
  ("espn:staff:2026-sleepers-busts-breakouts", "Fantasy football sleepers, busts and breakouts for 2026", "ESPN Fantasy staff", "2026-08-19", "sleepers_busts_breakouts", "ESPN analysts each select a sleeper, bust, or breakout based on draft cost, expected role, health, and offensive environment.", [
    t("Tyler Shough","sleeper","Bell cites Shough's strong late-2025 scoring, added weapons, and goal-line rushing."), t("C.J. Stroud","sleeper","Bowen expects line and backfield upgrades to restore Stroud's rhythm and weekly QB1 upside."), t("Kenyon Sadiq","sleeper","Dopp likes the low-cost rookie's hybrid WR/TE profile."), t("Jonathon Brooks","sleeper","Loza sees three-down upside at a deep discount if Brooks' knee holds."), t("Kenny Gainwell","sleeper","Moody sees stand-alone value after Gainwell averaged 17.8 points from Week 8 onward."), t("Cam Ward","sleeper","Yates is bullish after Tennessee upgraded Ward's supporting cast."),
    t("Mike Evans","bust","Clay flags age, injuries, and the touchdown fortune Evans may need to pay off."), t("Harold Fannin Jr.","bust","Cockcroft views Fannin's price as aggressive after a historic rookie season and major offensive changes."), t("Christian McCaffrey","bust","Dopp fades McCaffrey after an extreme workload."), t("Matthew Stafford","bust","Fulghum expects regression from career highs and sees little rushing floor at QB9 cost."), t("Malik Nabers","bust","Karabell prefers healthier early-round wideouts while Nabers recovers."), t("Josh Jacobs","bust","Moody cites age, accumulated touches, knee concerns, and declining efficiency."),
    t("Omarion Hampton","breakout","Bell sees a healthy line, Mike McDaniel, and dual-threat usage creating RB1 potential."), t("Emeka Egbuka","breakout","Bowen expects Egbuka to become Tampa Bay's top target after Mike Evans' exit."), t("Jeremiyah Love","breakout","Clay expects elite speed and three-down rookie volume."), t("Bhayshul Tuten","breakout","Cockcroft sees a clear high-end RB2 path after Travis Etienne's departure."), t("Luther Burden III","breakout","Fulghum cites vacated targets and elite per-route production."), t("Jadarian Price","breakout","Karabell likes Price's clearer Seattle path and large discount versus other rookies."), t("Ashton Jeanty","breakout","Yates expects improved Raiders infrastructure to unlock Jeanty's elite talent.")]),
  ("espn:karabell:2026-do-not-draft", "Fantasy Football 'Do Not Draft' list: Giants' young trio among players being overvalued", "Eric Karabell", "2026-08-05", "do_not_draft", "Karabell fades prominent players whose ADP assumes health, volume, efficiency, or immediate rookie impact that he does not trust.", [
    t("Malik Nabers","avoid","Nabers' knee recovery and high ADP create too much early-round uncertainty."), t("Jaxson Dart","avoid","Dart's price assumes a step forward despite an unstable Giants offense."), t("Cam Skattebo","avoid","Skattebo's health and role uncertainty make his draft price aggressive."), t("Josh Allen","avoid","Allen's second-round cost sacrifices too much value in a one-quarterback league."), t("Drake Maye","avoid","Maye faces a harder schedule at an elevated price."), t("Jayden Daniels","avoid","Daniels carries multi-injury risk at a premium cost."), t("Daniel Jones","avoid","Achilles recovery and efficiency questions reduce Jones' appeal."), t("Jordan Love","avoid","Low passing volume and little rushing cap Love's fantasy ceiling."), t("Christian McCaffrey","avoid","Age and a 400-plus-touch history create unacceptable first-round risk."), t("Kenneth Walker III","avoid","Walker has not delivered an RB1 season and is too expensive in Round 3."), t("Bucky Irving","avoid","Poor 2025 efficiency and Kenny Gainwell's presence threaten Irving's workload."), t("Rashee Rice","avoid","Availability, injury, and suspension uncertainty make Rice difficult to price."), t("A.J. Brown","avoid","Karabell sees decline and a difficult schedule, not a top-10 receiver."), t("Marvin Harrison Jr.","avoid","Harrison has not yet justified a WR2 price."), t("Kyle Pitts Sr.","avoid","One huge 2025 week and a top-five price make Pitts easy to pass."), t("Dallas Goedert","avoid","Touchdown regression and durability concerns weaken Goedert's case.")]),
  ("espn:karabell:2026-do-draft", "Fantasy Football 'Do Draft' list: Derrick Henry, Patrick Mahomes among undervalued players to pick", "Eric Karabell", "2026-08-12", "do_draft", "Karabell highlights proven veterans and discounted role winners whose prices leave room for useful fantasy returns.", [
    t("James Cook III","target","Cook remains a reliable early-round back whose role and production are being undervalued."), t("Derrick Henry","target","Henry's elite touchdown and rushing profile remains attractive despite age concerns."), t("Omarion Hampton","target","Hampton has early-round volume and receiving upside in an upgraded offense."), t("Josh Jacobs","target","Karabell views Jacobs as a discounted workhorse."), t("Chase Brown","target","Brown's every-down usage supports his early-round price."), t("Javonte Williams","target","Williams offers dependable volume after a strong 2025 season."), t("David Montgomery","target","Montgomery should lead Houston's backfield and regain touchdown volume."), t("Jadarian Price","target","Price is a discounted route to Seattle's vacated backfield work."), t("Kenny Gainwell","target","Gainwell offers stand-alone touches and contingency upside."), t("Rachaad White","target","White's receiving profile and Washington opportunity are inexpensive."), t("Brock Purdy","target","Purdy is a low-cost path to strong passing efficiency."), t("Patrick Mahomes II","target","Mahomes' price has fallen far enough to make the rebound worth targeting."), t("Kyler Murray","target","Murray offers inexpensive passing and rushing upside in Minnesota."), t("Justin Jefferson","target","Jefferson remains an elite talent available at a relative discount."), t("Josh Downs","target","Downs can absorb meaningful vacated volume."), t("Wan'Dale Robinson","target","Robinson's role knowledge and short-area volume create late value."), t("Tucker Kraft","target","Kraft offers a discounted ceiling if his ACL recovery stays on schedule."), t("Mark Andrews","target","Andrews' established scoring profile is inexpensive."), t("T.J. Hockenson","target","Hockenson is healthy and benefits from improved quarterback play."), t("Dalton Kincaid","target","Kincaid retains breakout potential at a reduced price."), t("Hunter Henry","target","Henry is an affordable late tight end with a stable role.")]),
  ("espn:moody:2026-draft-targets", "Eric Moody's draft-day targets: Kyler Murray, Kenny Gainwell among top values", "Eric Moody", "2026-08-18", "draft_targets", "Moody identifies values across positions plus five late fliers, emphasizing volume, offensive upgrades, and prices below projected roles.", [
    t("Jaxson Dart","target","Dart's rushing and connection with Malik Nabers create upside."), t("Dak Prescott","target","Prescott has an elite receiver duo and likely passing volume."), t("Kyler Murray","target","Murray gains Kevin O'Connell and a strong set of pass catchers."), t("Omarion Hampton","target","Hampton pairs volume with Mike McDaniel's scheme."), t("Breece Hall","target","Hall's projected workload and Geno Smith improve the rebound case."), t("Cam Skattebo","target","A run-heavy Giants approach gives Skattebo volume upside."), t("Kenny Gainwell","target","A more even Tampa Bay split makes Gainwell a value."), t("Garrett Wilson","target","Wilson should command volume with Geno Smith."), t("Terry McLaurin","target","A healthy McLaurin has room for more targets."), t("Michael Pittman Jr.","target","Pittman's possession skills fit Aaron Rodgers and Pittsburgh's vacated volume."), t("Jakobi Meyers","target","Meyers remains a steady producer at a discount."), t("Harold Fannin Jr.","target","Fannin's record-setting rookie year and David Njoku's exit support the price."), t("Blake Corum","target","Corum has a weekly role plus high-value insurance upside."), t("Josh Downs","target","Downs can capture a large share of Indianapolis' vacated targets."), t("Chris Godwin Jr.","target","A healthy Godwin can regain slot volume after Mike Evans' departure."), t("Jalen Coker","target","Carolina's extension signals trust and a larger role."), t("Cam Ward","target","Ward's post-bye improvement and upgraded weapons make him a late target.")]),
  ("espn:cockcroft:2026-deep-sleepers", "Carson Beck, Tre' Harris among deep fantasy football sleepers in 2026", "Tristan H. Cockcroft", "2026-08-20", "deep_sleepers", "Surfaces players generally available late or undrafted whose paths to snaps, targets, or contingency roles matter in deep leagues.", [
    t("Carson Beck","sleeper","Beck is a deep superflex stash with a plausible path to Arizona starts."), t("Greg Dulcich","sleeper","Miami's depleted pass-catcher room gives Dulcich a route to every-down work."), t("Tre' Harris","sleeper","Harris can earn a larger Chargers role after an uneven rookie season."), t("Ja'Kobi Lane","sleeper","Lane's size and opportunity give him red-zone and dynasty appeal."), t("MarShawn Lloyd","sleeper","Lloyd remains a talented contingency back if he can stay healthy."), t("Nicholas Singleton","sleeper","Singleton's athletic profile and Tennessee depth chart create late upside.")]),
  ("espn:florio:2026-rookie-late-rounds", "2026 NFL rookies to pick in later rounds of fantasy football drafts", "Michael F. Florio", "2026-08-25", "rookie_sleepers", "Organizes late-round rookies by league depth, separating redraft bench targets, deep-league fliers, dynasty stashes, and superflex quarterbacks.", [
    t("Jonah Coleman","sleeper","Coleman has a path to Denver touches and is viable in 10-team leagues."), t("Mike Washington Jr.","sleeper","Washington is a high-upside Raiders contingency back."), t("Emmett Johnson","sleeper","Johnson can earn passing-down work in Kansas City."), t("Caleb Douglas","sleeper","Douglas has an immediate opportunity in Miami's remade receiver room."), t("Chris Bell","sleeper","Bell is another inexpensive route to Miami targets."), t("De'Zhaun Stribling","sleeper","Stribling has a path to snaps in San Francisco's changing receiver group."), t("Ja'Kobi Lane","sleeper","Lane offers size and touchdown upside in Baltimore."), t("Kaelon Black","sleeper","Black is a deep San Francisco backfield stash."), t("Nicholas Singleton","sleeper","Singleton combines athletic upside with a reachable Tennessee role."), t("Zachariah Branch","sleeper","Branch is a dynasty stash whose playmaking can earn designed touches."), t("Antonio Williams","sleeper","Williams is a dynasty receiver stash in Washington."), t("Carson Beck","sleeper","Beck is a late superflex option with potential starting opportunity.")]),
  ("espn:karabell:2026-team-tiers", "Fantasy team tiers: Which NFL squad has the most fantasy value?", "Eric Karabell", "2026-07-02", "team_value_tiers", "Ranks entire NFL fantasy ecosystems by the number, quality, and reliability of draftable players. The article is retained as team-level context rather than converted into player target labels.", []),
  ("espn:karabell:2026-bounce-backs", "Fantasy football: 12 players who will bounce back this season", "Eric Karabell", "2026-07-07", "bounce_back", "Targets established players whose 2025 results were depressed by injury or situation and whose health, role, or supporting cast improved for 2026.", [
    t("Mike Evans","target","Evans is healthy in San Francisco and still showed late-2025 scoring ability."), t("Brock Purdy","target","Purdy is healthy after an injury-shortened year and gains a proven downfield receiver."), t("Kyler Murray","target","Murray is a cheap rebound bet after a lost Arizona season and now joins Minnesota."), t("David Montgomery","target","Montgomery should lead Houston's backfield with volume and touchdown upside."), t("Rachaad White","target","White's receiving skill and thin Washington competition make his ADP attractive."), t("Jonathon Brooks","target","Carolina believes Brooks is healthy and capable of challenging for passing-game work."), t("DJ Moore","target","Moore can return to WR2 form as Buffalo's best established receiver."), t("Terry McLaurin","target","A healthy McLaurin can resume his consistent 1,000-yard profile."), t("Chris Godwin Jr.","target","Late-2025 flashes support a healthy rebound at a low price."), t("Marvin Harrison Jr.","target","Improved health and a more balanced Arizona offense create a third-year rebound path."), t("Brock Bowers","target","A healthy knee and upgraded quarterback play can restore elite tight end production."), t("T.J. Hockenson","target","Improved health and Kyler Murray support a return to prominence.")]),
  ("espn:moody:2026-vacated-opportunity", "Fantasy football: Six players who benefit most from vacated targets and touches", "Eric Moody", "2026-07-21", "vacated_opportunity", "Uses offseason departures and projected volume to identify players positioned to inherit meaningful touches or targets.", [
    t("Kenneth Walker III","target","Kansas City's investment and open backfield point to more early-down, receiving, and goal-line work."), t("Terry McLaurin","target","Washington has the third-most vacated targets and little competition for its healthy No. 1 receiver."), t("Michael Pittman Jr.","target","Pittsburgh's vacated targets and Aaron Rodgers' short-area preferences fit Pittman's volume profile."), t("Bhayshul Tuten","target","Travis Etienne's departure leaves Tuten projected to lead Jacksonville's backfield touches."), t("Chig Okonkwo","target","Zach Ertz's exit and Washington's contract signal a larger role behind McLaurin."), t("Greg Dulcich","sleeper","Miami's vacated tight-end targets and thin receiver room give Dulcich an every-down path.")]),
]

URLS = [
"https://www.espn.com/fantasy/football/story/_/id/49517475/nfl-fantasy-football-rankings-running-back-handcuffs-insurance",
"https://www.espn.com/fantasy/football/story/_/id/49347450/fantasy-football-rankings-top-players-avoid-2026-drafts",
"https://www.espn.com/fantasy/football/story/_/page/FFSleepBustBreak26-49030808/fantasy-football-2026-rankings-nfl-sleepers-breakouts-busts",
"https://www.espn.com/fantasy/football/story/_/id/49529494/2026-fantasy-football-busts-overvalued-do-not-draft-karabell",
"https://www.espn.com/fantasy/football/story/_/id/49556816/2026-fantasy-football-sleepers-value-picks-undervalued-karabell",
"https://www.espn.com/fantasy/football/story/_/id/49639036/fantasy-football-targets-draft-values-sleepers-breakouts",
"https://www.espn.com/fantasy/football/story/_/id/49652186/2026-fantasy-football-sleepers-nfl-deep-leagues",
"https://www.espn.com/fantasy/football/story/_/id/49702808/2026-fantasy-football-sleepers-nfl-rookie-dynasty-leagues",
"https://www.espn.com/fantasy/football/story/_/id/49250055/espn-nfl-fantasy-football-team-rankings-value",
"https://www.espn.com/fantasy/football/story/_/id/49290760/fantasy-football-players-bounce-back-season",
"https://www.espn.com/fantasy/football/story/_/id/49401787/espn-nfl-fantasy-football-advice-players-benefit-vacated-targets"]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, (source_id, title, author, published, content_type, summary, takeaways) in enumerate(SOURCES):
        artifact = {"metadata":{"schema_version":1,"build_id":BUILD_ID,"built_at":"2026-08-26T21:00:00Z","season":2026,"takeaway_count":len(takeaways)},"source":{"id":source_id,"source_key":"espn","title":title,"author":author,"url":URLS[index],"published_at":published,"season":2026,"content_type":content_type,"summary":summary},"takeaways":takeaways}
        filename = source_id.replace(":", "_") + ".json"
        (OUT / filename).write_text(json.dumps(artifact, indent=2) + "\n")
        paths.append(f"data/processed/fantasy_analysis/{BUILD_ID}/{filename}")
    pointer_path = ROOT / "data/processed/fantasy_analysis/latest.json"
    current = json.loads(pointer_path.read_text())
    current["artifacts"] = [path for path in current["artifacts"] if "/espn_" not in path] + paths
    pointer_path.write_text(json.dumps(current, indent=2) + "\n")
    print(json.dumps({"sources":len(SOURCES),"takeaways":sum(len(row[-1]) for row in SOURCES),"output":str(OUT)}))

if __name__ == "__main__":
    main()
