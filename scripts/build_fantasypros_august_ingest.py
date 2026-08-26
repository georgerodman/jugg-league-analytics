#!/usr/bin/env python3
"""Build reviewed artifacts for the FantasyPros sources supplied on 2026-08-26.

This is ingestion-only. It intentionally does not call the summary model or
advance the fantasy_research summary pointer.
"""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = "20260826T234500Z"
BUILT_AT = "2026-08-26T23:45:00Z"
OUT = ROOT / "data/processed/fantasy_analysis" / BUILD
DB = ROOT / ".local/renegade-draft-room.sqlite"
PLAYERS = {name: player_id for player_id, name in sqlite3.connect(DB).execute("SELECT id, display_name FROM players")}


def takeaway(name, label, summary, risks=(), formats=("redraft", "half-PPR"), price=None, sentiment=None):
    player_id = PLAYERS.get(name)
    if not player_id:
        return None
    return {
        "player_id": player_id,
        "player_name": name,
        "label": label,
        "sentiment": sentiment or ("negative" if label in ("avoid", "bust") else "positive"),
        "summary": summary,
        "rationale": summary,
        "risks": list(risks),
        "formats": list(formats),
        "price_condition": price,
        "assumptions": [],
    }


def source(source_id, title, author, url, published_at, content_type, summary, rows):
    return {
        "id": source_id,
        "title": title,
        "author": author,
        "url": url,
        "published_at": published_at,
        "content_type": content_type,
        "summary": summary,
        "takeaways": [row for row in rows if row],
    }


wr_experts = [
    ("Parker Washington", "breakout", "Multiple featured experts see a sixth-round WR30 price as conservative after his elite late-2025 usage and production, with a path to leading Jacksonville's ambiguous receiver room.", ["Brian Thomas Jr. and Travis Hunter can keep the target hierarchy crowded."], "WR30 / pick 69"),
    ("Luther Burden III", "breakout", "Burden's rookie efficiency and expected Year 2 role in Ben Johnson's offense create major upside at WR25 cost.", ["A groin injury could linger and Chicago has several strong target competitors."], "WR25"),
    ("Christian Watson", "value", "Watson's efficiency, expanded opportunity after receiver departures, and WR28-WR29 cost give him WR1/WR2 upside.", ["His extensive injury history remains the central concern."], "WR28-WR29"),
    ("Rome Odunze", "breakout", "Odunze's strong pre-injury 2025 start and DJ Moore's departure create a cleaner path to a full-season breakout.", ["Luther Burden and Colston Loveland still compete for targets."], "WR29"),
    ("Emeka Egbuka", "breakout", "Egbuka's early-2025 production and Mike Evans' vacated role support top-12 upside if he establishes himself as Tampa Bay's lead receiver.", ["A current toe injury and target hierarchy introduce uncertainty."], None),
    ("DJ Moore", "value", "Moore is priced as WR26 despite stepping into a plausible lead-receiver role with Josh Allen in Buffalo.", ["His exact share in a new offense is projected rather than established."], "WR26"),
    ("Marvin Harrison Jr.", "value", "A new McVay-influenced offense and WR32 price create a post-hype rebound case for Harrison.", ["His first two seasons and Arizona's target competition leave the rebound unproven."], "WR32"),
    ("Chris Olave", "breakout", "Olave already owns alpha usage, and even modest quarterback improvement could turn his WR11-WR13 cost into a top-five outcome.", ["This is a premium-cost breakout case rather than a late sleeper."], "WR11-WR13"),
    ("Davante Adams", "value", "Adams' dominant red-zone role gives him half-PPR value despite expected touchdown regression.", ["Age, health, and a relatively rich WR23 price reduce the margin for error."], "WR23"),
    ("Jameson Williams", "breakout", "Williams combines established 1,100-yard production, vertical usage, and possible touchdown growth at a WR25 price.", ["The case still depends on consistent volume and scoring progression."], "WR25"),
    ("KC Concepcion", "sleeper", "Concepcion offers a late chance to capture Cleveland's lead-receiver role because of his separation and after-catch ability.", ["Cleveland's quarterback play and overall offense can cap the ceiling."], "WR49 / double-digit rounds"),
    ("Ja'Kobi Lane", "sleeper", "Lane's camp momentum and opportunity opposite Zay Flowers make him a near-free rookie upside bet.", ["The role is based on camp reports and an unsettled Baltimore target tree."], "WR92 / final rounds"),
    ("Tre Tucker", "sleeper", "Tucker already owns heavy playing time and can convert more designed touches into a breakout at WR60 cost.", ["Las Vegas still must create a productive passing environment."], "WR60"),
    ("Deebo Samuel Sr.", "sleeper", "Samuel's return to Kyle Shanahan creates a plausible manufactured-touch role and WR3 output at WR55 cost.", ["Age and whether San Francisco restores his former usage are material assumptions."], "WR55"),
    ("De'Zhaun Stribling", "sleeper", "Stribling's preseason production, draft capital, and San Francisco's injuries give him an inexpensive path to early targets.", ["Deebo Samuel's return and recovering veterans can compress the role."], "Outside WR50"),
    ("Wan'Dale Robinson", "sleeper", "Robinson's prior volume and continuity with Brian Daboll make WR48 a potentially favorable price in Tennessee.", ["Carnell Tate and Calvin Ridley create meaningful target competition."], "WR48"),
    ("Josh Downs", "sleeper", "Downs' strong target-earning rate and Indianapolis' vacated volume give him a path to beat WR41.", ["Keenan Allen adds competition and the case is strongest in reception formats."], "WR41"),
    ("Matthew Golden", "sleeper", "Green Bay's departures and a potentially tighter rotation give Golden a path to lead the team in targets at WR50.", ["His NFL production remains limited and the Packers retain other established options."], "WR50"),
    ("Dontayvion Wicks", "sleeper", "Wicks has a path to Philadelphia's WR2 job and substantial playing time at a WR64 price.", ["Rookie Makai Lemon can challenge him once healthy."], "WR64"),
    ("Jalen Nailor", "sleeper", "Nailor's open-field ability and reunion with Kirk Cousins create a nearly free upside case in Las Vegas.", ["Tre Tucker may be the clearer lead receiver and Fernando Mendoza could eventually change the offense."], "WR68"),
    ("Kayshon Boutte", "sleeper", "Boutte's move to Houston opens a path to the No. 2 receiver role at a final-round price.", ["The new role is not secured and his ADP may rise quickly."], "WR79 / pick 160"),
]

busts = [
    takeaway("Rashee Rice", "bust", "Rice's WR13 cost does not adequately discount knee recovery, availability, off-field, and changing offensive-balance risks.", ["He remains Kansas City's most physically imposing receiver when active."], price="WR13"),
    takeaway("Davante Adams", "bust", "Adams' WR8 finish leaned heavily on 14 touchdowns, making age, lower-body injuries, and likely red-zone regression dangerous at his price.", ["His route skill and established Rams role preserve upside."], price="Premium WR cost"),
    takeaway("Christian Watson", "bust", "Watson's talent and expanded opportunity are outweighed by a long injury history and uncertainty that he can sustain lead-receiver volume.", ["Green Bay extended him and lost two competing receivers."], price="WR3 range"),
    takeaway("Carnell Tate", "bust", "Tate's rookie price assumes a quick breakout in an offense with quarterback, line, and target-competition concerns.", ["He can become Tennessee's focal point later in the season."], price="Premium rookie WR cost"),
]

late_round_names = [
    ("Chris Rodriguez Jr.", 123, "RB43", 23), ("Jalen Coker", 125, "WR51", 33), ("Khalil Shakir", 127, "WR52", 27),
    ("Jordan Love", 130, "QB19", 12), ("Tyler Shough", 133, "QB20", 22), ("Tyjae Spears", 135, "RB46", 25),
    ("Juwan Johnson", 137, "TE16", 16), ("Malik Willis", 138, "QB21", 14), ("Keaton Mitchell", 139, "RB47", 25),
    ("Tank Bigsby", 140, "RB48", 23), ("C.J. Stroud", 146, "QB22", 23), ("Chig Okonkwo", 147, "TE18", 14),
    ("Dylan Sampson", 150, "RB52", 49), ("Denzel Boston", 152, "WR57", 14), ("Daniel Jones", 154, "QB24", 21),
    ("Adonai Mitchell", 155, "WR59", 82), ("Dalton Schultz", 156, "TE20", 26), ("Cam Ward", 157, "QB25", 15),
    ("Tre Tucker", 160, "WR60", 59), ("Jauan Jennings", 161, "WR61", 13), ("Jalen McMillan", 162, "WR62", 23),
    ("Braelon Allen", 164, "RB56", 43), ("AJ Barner", 166, "TE22", 18), ("Dontayvion Wicks", 170, "WR65", 52),
    ("Tre' Harris", 172, "WR66", 54),
]

wr_sleepers = [
    ("Stefon Diggs", 1, 13, 44, 45), ("Deebo Samuel Sr.", 2, 10, 54, 52), ("De'Zhaun Stribling", 3, 9, 56, 47),
    ("Rashid Shaheed", 4, 6, 57, 53), ("Denzel Boston", 5, 5, 58, 60), ("Jalen McMillan", 6, 5, 63, 64),
    ("Jalen Nailor", 7, 5, 73, 59), ("Ryan Flournoy", 8, 6, 68, 84), ("Omar Cooper Jr.", 9, 2, 65, 71),
    ("Tre' Harris", 10, 2, 70, 74), ("Jaylin Noel", 11, 2, 67, 97), ("Dontayvion Wicks", 12, 3, 69, 77),
    ("Kayshon Boutte", 13, 1, 64, 75), ("Keenan Allen", 14, 2, 75, 61), ("Tank Dell", 15, 2, 77, 70),
    ("Antonio Williams", 16, 3, 82, 85), ("Tre Tucker", 17, 1, 62, 73), ("Devaughn Vele", 18, 1, 88, 88),
    ("Isaac TeSlaa", 19, 1, 78, 66), ("Malik Washington", 20, 1, 72, 69), ("Jack Bech", 21, 1, 87, 99),
    ("Elijah Sarratt", 22, 1, 92, None), ("Pat Bryant", 23, 2, 71, 82), ("Jerry Jeudy", 24, 1, 60, 72),
    ("Rashod Bateman", 25, 1, 80, None), ("Adonai Mitchell", 26, 1, 61, 81), ("Travis Hunter", 27, 1, 66, 63),
    ("Malachi Fields", 28, 1, 86, 79), ("Ted Hurst III", 29, 1, 93, 89), ("Caleb Douglas", 30, 1, 97, 76),
    ("Cyrus Allen", 31, 1, 102, 68),
]

dynasty_rookies = [
    ("Jeremiyah Love", 1, "RB1", 1), ("Carnell Tate", 2, "WR1", 1), ("Jordyn Tyson", 3, "WR2", 1),
    ("Makai Lemon", 4, "WR3", 1), ("Jadarian Price", 5, "RB2", 1), ("KC Concepcion", 6, "WR4", 2),
    ("Omar Cooper Jr.", 7, "WR5", 2), ("Fernando Mendoza", 8, "QB1", 2), ("Denzel Boston", 9, "WR6", 2),
    ("Kenyon Sadiq", 10, "TE1", 2), ("Jonah Coleman", 11, "RB3", 2), ("Eli Stowers", 12, "TE2", 2),
    ("De'Zhaun Stribling", 13, "WR7", 3), ("Ja'Kobi Lane", 14, "WR8", 3), ("Germie Bernard", 15, "WR9", 3),
    ("Emmett Johnson", 16, "RB4", 3), ("Antonio Williams", 17, "WR10", 3), ("Chris Bell", 18, "WR11", 3),
    ("Nicholas Singleton", 19, "RB5", 4), ("Ty Simpson", 20, "QB2", 4), ("Ted Hurst III", 21, "WR12", 4),
    ("Elijah Sarratt", 22, "WR13", 4), ("Mike Washington Jr.", 23, "RB6", 4), ("Kaelon Black", 24, "RB7", 4),
    ("Malachi Fields", 25, "WR14", 4), ("Kaytron Allen", 26, "RB8", 4), ("Zachariah Branch", 27, "WR15", 4),
    ("Eli Raridon", 28, "TE3", 4), ("Max Klare", 29, "TE4", 4), ("Oscar Delp", 30, "TE5", 4),
]

SOURCES = [
    source("fantasypros:featured-pros:2026-wr-sleepers-breakouts", "21 WR Sleepers & Breakouts Experts Love", "FantasyPros Featured Pros", "https://www.fantasypros.com/2026/08/21-wide-receiver-sleepers-breakouts-experts-love-2026-fantasy-football/", "2026-08-26", "expert_roundup", "Featured analysts identify breakout and sleeper receivers at current half-PPR prices.", [takeaway(name, label, summary, risks, price=price) for name, label, summary, risks, price in wr_experts]),
    source("fantasypros:tarracciano:2026-wr-busts-aug26", "4 Fantasy Football Busts to Avoid: Wide Receivers", "Evan Tarracciano", "https://www.fantasypros.com/2026/08/4-fantasy-football-busts-to-avoid-wide-receivers-2026-2/", "2026-08-26", "busts", "Four receivers whose current draft prices do not sufficiently account for health, role, or offensive uncertainty.", busts),
    source("fantasypros:ammirante:2026-wr-sleepers", "3 Fantasy Football Sleepers: Wide Receivers", "Frank Ammirante", "https://www.fantasypros.com/2026/08/3-fantasy-football-sleepers-wide-receivers-2026/", "2026-08-26", "sleepers", "Three final-round receiver bets based primarily on paths to volume.", [
        takeaway("Tre Tucker", "sleeper", "Tucker has emerged as Las Vegas' lead receiver and has rapport with Kirk Cousins, creating a clear path to late-round volume.", ["The offense and quarterback transition still limit certainty."], price="Final rounds"),
        takeaway("Kayshon Boutte", "sleeper", "Boutte's trade to Houston gives him a plausible No. 2 role and deep-target opportunity with C.J. Stroud.", ["His ADP may rise and the role must be confirmed."], price="Final rounds"),
        takeaway("Malik Washington", "sleeper", "Washington is a PPR-oriented bet to lead Miami in receptions because of limited established target competition.", ["Miami may be run-heavy and the underneath role is less valuable in non-PPR."], price="Final rounds"),
    ]),
    source("fantasypros:staff:2026-late-round-25", "Fantasy Football: 25 Late-Round Draft Picks Experts Love", "FantasyPros Staff", "https://www.fantasypros.com/2026/08/fantasy-football-25-late-round-draft-picks-experts-love-2026/", "2026-08-26", "ranking_values", "Twenty-five late-round players whose expert consensus rank is ahead of average draft position.", [takeaway(name, "value", f"FantasyPros ranks {name} overall No. {rank} ({pos}), {delta} spots ahead of ADP, identifying a late-round value.", ["Ranking gaps are market signals, not standalone role analysis."], price=f"Overall ECR {rank}; {delta} spots ahead of ADP") for name, rank, pos, delta in late_round_names]),
    source("fantasypros:shepardson:2026-late-rb", "3 Late-Round Running Backs to Draft", "Josh Shepardson", "https://www.fantasypros.com/2026/08/fantasy-football-3-late-round-running-backs-to-draft-2026/", "2026-08-26", "late_round_targets", "Three half-PPR running backs available after pick 120 who offer usable roles or contingent upside.", [
        takeaway("Aaron Jones", "value", "Jones lacks a league-winning ceiling but can beat RB40 cost through receiving work and early-season FLEX utility.", ["Age, declining efficiency, missed games, and Jordan Mason cap the ceiling."], price="ADP 121 / RB40"),
        takeaway("Keaton Mitchell", "sleeper", "Mitchell's explosiveness and fit in Mike McDaniel's offense can support standalone value plus injury-contingent upside.", ["He is not expected to overtake Omarion Hampton."], price="ADP 146 / RB47"),
        takeaway("Kaytron Allen", "sleeper", "Allen is a final-round bet to win Washington's early-down and goal-line work.", ["Jonah Coleman is favored to finish higher and Allen offers little receiving production."], price="ADP 200 / RB60"),
    ]),
    source("fantasypros:iacona:2026-breakout-te", "4 Breakout Tight Ends to Target", "Lawrence Iacona", "https://www.fantasypros.com/2026/08/4-breakout-tight-ends-to-target-2026-fantasy-football/", "2026-08-26", "breakouts", "Four tight ends with expanding usage, favorable environments, or high-end efficiency.", [
        takeaway("Brenton Strange", "breakout", "Strange's 2025 foundation and potential target-share growth give him a path to consistent TE1 production.", ["He was only Jacksonville's fourth passing option last season."], price="Mid rounds"),
        takeaway("AJ Barner", "breakout", "Barner's reliable 2025 receiving line and Seattle's early backfield uncertainty could increase passing and red-zone opportunity.", ["The projected passing shift and red-zone growth are assumptions."], price="Late rounds"),
        takeaway("Gunnar Helm", "breakout", "Helm's contested-catch and red-zone traits create touchdown upside as Tennessee modernizes its passing game.", ["His rookie volume was modest and Cam Ward must improve."], price="Late rounds"),
        takeaway("Tucker Kraft", "breakout", "Kraft's elite pre-injury pace and central Green Bay role give him top-five tight-end potential when healthy.", ["The case depends on a durable return from his Week 9 injury."], price="Mid rounds"),
    ]),
    source("fantasypros:ecr:2026-dynasty-rookies", "2026 Dynasty Rookie Rankings", "FantasyPros Expert Consensus", "https://www.fantasypros.com/nfl/rankings/dynasty-rookies-overall.php", "2026-08-26", "dynasty_rankings", "Consensus dynasty rookie ranks. Stored as format context and excluded from the redraft positive/negative vote by using mixed sentiment.", [takeaway(name, "target", f"FantasyPros dynasty rookie consensus ranks {name} No. {rank} overall ({pos}) in tier {tier}.", ["Dynasty rookie value should not be treated as a 2026 redraft recommendation."], formats=("dynasty", "rookie"), price=f"Dynasty rookie rank {rank}; tier {tier}", sentiment="mixed") for name, rank, pos, tier in dynasty_rookies]),
    source("fantasypros:ecr:2026-wr-sleepers", "2026 Fantasy Football WR Sleepers Rankings", "FantasyPros Expert Consensus", "https://www.fantasypros.com/nfl/rankings/wr-sleepers.php", "2026-08-26", "sleeper_rankings", "A dated half-PPR sleeper ranking aggregated from 25 experts, with player-level expert counts, ECR, and ADP.", [takeaway(name, "sleeper", f"FantasyPros' half-PPR sleeper board ranks {name} No. {rank}, based on {experts} contributing expert{'s' if experts != 1 else ''}, with WR ECR {ecr}{f' and ADP {adp}' if adp else ''}.", ["Expert participation varies substantially by player and this is half-PPR context."], price=f"Sleeper rank {rank}; WR ECR {ecr}") for name, rank, experts, ecr, adp in wr_sleepers]),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = []
    for item in SOURCES:
        rows = item.pop("takeaways")
        artifact = {
            "metadata": {"schema_version": 2, "build_id": BUILD, "built_at": BUILT_AT, "season": 2026, "takeaway_count": len(rows)},
            "source": {"source_key": "fantasypros", "season": 2026, **item},
            "takeaways": rows,
        }
        filename = item["id"].replace(":", "_") + ".json"
        (OUT / filename).write_text(json.dumps(artifact, indent=2) + "\n")
        paths.append(f"data/processed/fantasy_analysis/{BUILD}/{filename}")
    pointer = ROOT / "data/processed/fantasy_analysis/latest.json"
    data = json.loads(pointer.read_text())
    data["artifacts"] = [path for path in data["artifacts"] if f"/{BUILD}/" not in path] + paths
    pointer.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps({"sources": len(SOURCES), "takeaways": sum(json.loads((ROOT / path).read_text())["metadata"]["takeaway_count"] for path in paths)}))


if __name__ == "__main__":
    main()
