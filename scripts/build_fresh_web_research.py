#!/usr/bin/env python3
"""Ingest independently researched late-August sources without refreshing AI summaries."""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = "20260827T033000Z"
BUILT_AT = "2026-08-27T03:30:00Z"
OUT = ROOT / "data/processed/fantasy_analysis" / BUILD
DB = ROOT / ".local/renegade-draft-room.sqlite"
PLAYERS = {name: player_id for player_id, name in sqlite3.connect(DB).execute("SELECT id,display_name FROM players")}


def takeaway(name, label, summary, risks=(), price=None, sentiment=None):
    player_id = PLAYERS.get(name)
    if not player_id:
        raise ValueError(f"Unknown player: {name}")
    return {
        "player_id": player_id,
        "player_name": name,
        "label": label,
        "sentiment": sentiment or ("negative" if label in ("avoid", "bust") else "positive"),
        "summary": summary,
        "rationale": summary,
        "risks": list(risks),
        "formats": ["redraft", "PPR"],
        "price_condition": price,
        "assumptions": [],
    }


def source(source_id, key, title, author, url, published_at, content_type, summary, rows):
    return {
        "id": source_id,
        "source_key": key,
        "title": title,
        "author": author,
        "url": url,
        "published_at": published_at,
        "content_type": content_type,
        "summary": summary,
        "takeaways": rows,
    }


SOURCES = [
    source(
        "cbs:cummings:2026-deep-sleepers-aug26", "cbs_sports",
        "2026 Fantasy football deep sleepers: Projections say Tyler Shough and Tre Tucker are steals",
        "Heath Cummings",
        "https://secure-www.cbssports.com/fantasy/football/news/2026-fantasy-football-deep-sleepers-projections/",
        "2026-08-26", "deep_sleepers",
        "Projection-backed and conditional late-round values, all carrying CBS ADPs outside the top 150 or no ADP.",
        [
            takeaway("Tyler Shough", "sleeper", "Shough's 2025 starting pace, projected touchdown growth, and eventual access to a healthy receiving group create QB1 upside at a QB21 price.", ["Early-season receiving health can cap the ceiling."], "ADP 153 / QB21"),
            takeaway("Jalen Coker", "sleeper", "Coker projects as a top-32 receiver and can benefit from more slot usage after already producing efficiently on limited opportunity.", ["Carolina still has a developing target hierarchy."], "ADP 154; worth a Round 10-11 reach"),
            takeaway("Malik Willis", "sleeper", "Willis' rushing production gives him a strong chance to beat QB23 pricing even if Miami remains a weak offense.", ["Passing volume and offensive quality may limit weekly consistency."], "ADP 162 / upside QB2"),
            takeaway("Dalton Schultz", "value", "Schultz projects near the TE1 boundary on another 100-plus targets and has top-eight upside with better touchdown luck.", ["Touchdown improvement is not guaranteed."], "ADP 173 / TE13 projection"),
            takeaway("Tre Tucker", "sleeper", "Tucker has emerged as the Raiders' lead receiver and projects to beat his price substantially even before giving him a full coordinator-WR1 target share.", ["Brock Bowers remains the passing game's central target and the offense may be weak."], "ADP 186"),
            takeaway("Jonah Coleman", "sleeper", "Coleman would project for roughly 15 touches per game behind a strong line if J.K. Dobbins misses time.", ["His useful role depends heavily on a Dobbins absence."], "ADP 161 / contingency value"),
            takeaway("Keaton Mitchell", "sleeper", "Mitchell's extreme efficiency and possible receiving role give him a path to weekly value without fully displacing Omarion Hampton.", ["The case extrapolates from very low career volume."], "ADP 163"),
            takeaway("Keenan Allen", "value", "Allen can remain a high-volume PPR flex at a near-free price if he continues earning targets in Indianapolis.", ["Age and competition from younger Colts receivers can reduce his role."], "ADP 180 / deep PPR leagues"),
            takeaway("Chris Bell", "sleeper", "A fully recovered Bell could be Miami's most talented receiver and a final-round source of size, speed, and late-season upside.", ["His ACL recovery and actual starting role remain uncertain."], "Final round"),
        ],
    ),
    source(
        "nbc:rotoworld-staff:2026-sleepers-aug18", "nbc_rotoworld",
        "Fantasy Football Sleepers 2026: Keaton Mitchell, Jaydon Blue among Rotoworld staff picks",
        "Rotoworld Staff",
        "https://www.nbcsports.com/fantasy/football/news/fantasy-football-sleepers-2026-keaton-mitchell-jaydon-blue-among-rotoworld-staff-picks",
        "2026-08-18", "staff_sleepers",
        "Staff sleeper selections emphasizing opportunity and value relative to current draft position.",
        [
            takeaway("David Montgomery", "sleeper", "Montgomery can command close to a workhorse share in Houston because the incumbent backs have not established trusted passing-down roles.", ["Woody Marks will still have a role and an 80-percent snap projection is aggressive."], "RB20 range"),
            takeaway("Keaton Mitchell", "sleeper", "Mitchell's explosive career efficiency and expected passing-game use fit Mike McDaniel's offense and can create a PPR floor behind Hampton.", ["His NFL workload remains a small sample and he may stay a clear backup."], "Late rounds"),
            takeaway("Josh Downs", "sleeper", "Downs can expand beyond a slot-only role amid Indianapolis' thin healthy receiver group, and Keenan Allen need not block his full route tree.", ["Allen and Tyler Warren still compete for underneath targets."], "Discounted WR price"),
            takeaway("Bucky Irving", "value", "Irving already produced as a top-20 PPR back while hurt and can beat cost by pairing his 2024 efficiency with his 2025 workload.", ["His 2025 inefficiency and injury history remain concerns."], "Current RB price"),
            takeaway("KC Concepcion", "sleeper", "Concepcion can lead Cleveland in receptions because he can win at multiple depths and adapt to either likely quarterback style.", ["Cleveland's quarterback quality creates a low offensive floor."], "Double-digit rounds"),
            takeaway("Michael Pittman Jr.", "sleeper", "Pittman's short-area reliability fits a pass-heavier Pittsburgh offense and can produce steady PPR volume immediately.", ["The role may be useful rather than high-ceiling."], "PPR formats"),
            takeaway("Jaydon Blue", "sleeper", "Blue still has a plausible path to Dallas' third-down role and could become a cheap PPR specialist in a pass-heavy offense.", ["He contributed almost nothing as a rookie and camp praise may not translate."], "Late rounds"),
            takeaway("Wan'Dale Robinson", "value", "Robinson brings consecutive 140-target seasons into a familiar Brian Daboll system and is priced as a WR4 after a WR2 PPR finish.", ["Tennessee's overall passing ceiling is uncertain."], "WR4 price"),
            takeaway("Dallas Goedert", "value", "Goedert should remain a top-12 candidate because Philadelphia lost major target volume and did not add proven competition.", ["His 11-touchdown season is unlikely to repeat."], "TE15"),
        ],
    ),
    source(
        "nbc:rotoworld-staff:2026-busts-aug20", "nbc_rotoworld",
        "Fantasy Football Busts 2026: Omarion Hampton, Cam Skattebo among Rotoworld's top fades",
        "Rotoworld Staff",
        "https://www.nbcsports.com/fantasy/football/news/fantasy-football-busts-2026-omarion-hampton-cam-skattebo-among-rotoworlds-top-fades",
        "2026-08-20", "staff_busts",
        "Price-sensitive staff fades based on injuries, role competition, scheme fit, and inflated ADP.",
        [
            takeaway("Alec Pierce", "bust", "Pierce's surgically treated ankle and likely one-dimensional role make his current price difficult to justify.", ["A healthy return could restore his established deep role."], "Fade at current ADP"),
            takeaway("Omarion Hampton", "bust", "Hampton's poor zone-running results create scheme-fit risk under Mike McDaniel, while Keaton Mitchell can take enough work to hurt the price.", ["A large lead role behind a good line can overcome the efficiency concern."], "Early-round price"),
            takeaway("Cam Skattebo", "bust", "Skattebo's inefficiency, contact-heavy style, and return from a major leg injury make his mid-RB2 price fragile.", ["The rebuilt run game and prior high-volume production preserve upside."], "Mid RB2"),
            takeaway("Terry McLaurin", "bust", "McLaurin now faces legitimate target competition from Stefon Diggs in a scramble-heavy offense and has rarely produced above low-end WR2 levels.", ["He remains Washington's expected WR1."], "Low-end WR2"),
            takeaway("Bhayshul Tuten", "bust", "Tuten faces third-down and power-role competition in a backfield that can become an unsatisfying committee.", ["His athleticism still gives him the highest individual ceiling in the group."], "Elevated lead-back price"),
            takeaway("Luther Burden III", "bust", "Burden's physical playing style, current groin injury, and crowded young offense threaten both availability and target share.", ["His talent can still win a large role when healthy."], "Current WR price"),
            takeaway("Kenneth Walker III", "bust", "Walker is priced at a career high despite Kansas City's pass preference, committee history, and his limited receiving production.", ["The contract and improved team context can still produce a larger role."], "RB8 / first two rounds"),
            takeaway("DJ Moore", "bust", "Moore's declining route efficiency, weak separation indicators, and low target rate make an immediate Buffalo rebound a risky assumption.", ["Josh Allen and an open depth chart provide a strong environment."], "Current WR2/3 price"),
            takeaway("Parker Washington", "bust", "Washington's WR30 price leaves little room for Travis Hunter, Brian Thomas Jr., and Jakobi Meyers to claim healthy target shares.", ["Washington's late-2025 production supports a genuine lead-receiver case."], "WR30"),
            takeaway("Sam LaPorta", "bust", "LaPorta's crowded offense and multi-year injury history create more downside than his premium tight-end cost reflects.", ["He remains a proven, talented scorer in an elite offense."], "Premium TE price"),
        ],
    ),
    source(
        "rotowire:coventry:2026-dark-horse-sleepers", "rotowire",
        "2026 Fantasy Football Sleepers: 12 Dark Horse Candidates to Win Your League",
        "Jim Coventry",
        "https://www.rotowire.com/football/article/2026-fantasy-football-sleepers-12-dark-horse-candidates-to-win-your-league-128019",
        "2026-08-14", "late_round_values",
        "Twelve players with ADPs beyond pick 100 whose opportunity, scheme, or contingent role can substantially outperform cost.",
        [
            takeaway("Jordan Addison", "value", "Addison's touchdown decline tracks poor quarterback play, and Kyler Murray can restore top-24 upside at a WR4 price.", ["Offseason baggage and competition from Minnesota's other targets remain."], "Pick 100"),
            takeaway("Jordan Mason", "sleeper", "Mason has already produced efficiently behind Minnesota's strong line and becomes a major value if the aging Aaron Jones misses time.", ["His receiving work and standalone volume are minimal when Jones plays."], "Pick 106 / handcuff"),
            takeaway("Dalton Kincaid", "sleeper", "Kincaid's elite route efficiency and explosive usage create league-winning upside at a TE1/2 border price.", ["PCL trouble, missed games, and possible snap restrictions materially lower the floor."], "Pick 114"),
            takeaway("Tyrone Tracy Jr.", "value", "Tracy offers a stable receiving floor and becomes a lead option if Cam Skattebo misses time.", ["A healthy Skattebo controls early downs and caps Tracy's standalone ceiling."], "Pick 128"),
            takeaway("Baker Mayfield", "value", "Mayfield's pre-injury top-12 pace and scheme continuity make him a cheap quarterback with a proven ceiling.", ["He has played through injuries that materially damaged his production."], "Pick 130"),
            takeaway("Mark Andrews", "value", "Andrews can rebound after Baltimore cleared tight-end competition and recommitted to him in an offense expected to feature the position.", ["His 2025 separation and efficiency decline may reflect real aging."], "Pick 131 / TE2"),
            takeaway("Kyler Murray", "sleeper", "Murray's rushing floor, Kevin O'Connell's system, elite receivers, and improved protection create top-10 upside at a late QB price.", ["Durability has remained an important concern."], "Pick 136"),
            takeaway("Chris Rodriguez Jr.", "value", "Rodriguez has a clear early-down and goal-line role in an ascending Jacksonville offense with room to gain work if Tuten falters.", ["Six career receptions leave almost no PPR floor."], "Pick 142"),
            takeaway("De'Zhaun Stribling", "sleeper", "Stribling's draft capital and ideal Shanahan fit give him a path to early opportunity in an older, injury-prone receiver room.", ["He remains a rookie stash without a guaranteed starting role."], "Pick 145"),
            takeaway("Jalen Nailor", "sleeper", "Nailor's speed, contract, and scheme familiarity give him a legitimate chance to win a large role in Las Vegas.", ["His NFL production has not yet established starter-level ability."], "Pick 151"),
            takeaway("Ryan Flournoy", "sleeper", "Flournoy owns a stable third-receiver role in a strong passing offense and becomes immediately useful if either star receiver misses time.", ["His normal role remains behind two high-volume stars."], "Pick 163 / deep leagues"),
            takeaway("T.J. Hockenson", "sleeper", "Hockenson's underlying openness and catch rate can translate into a late-career bounce-back with Kyler Murray restoring passing volume.", ["Age and a sharp recent production decline remain meaningful."], "Pick 204 / TE20"),
        ],
    ),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = []
    for item in SOURCES:
        rows = item["takeaways"]
        artifact = {
            "metadata": {
                "schema_version": 2,
                "build_id": BUILD,
                "built_at": BUILT_AT,
                "season": 2026,
                "takeaway_count": len(rows),
            },
            "source": {
                "id": item["id"],
                "source_key": item["source_key"],
                "title": item["title"],
                "author": item["author"],
                "url": item["url"],
                "published_at": item["published_at"],
                "season": 2026,
                "content_type": item["content_type"],
                "summary": item["summary"],
            },
            "takeaways": rows,
        }
        filename = item["id"].replace(":", "_") + ".json"
        (OUT / filename).write_text(json.dumps(artifact, indent=2) + "\n")
        paths.append(f"data/processed/fantasy_analysis/{BUILD}/{filename}")

    pointer_path = ROOT / "data/processed/fantasy_analysis/latest.json"
    pointer = json.loads(pointer_path.read_text())
    pointer["artifacts"] = [path for path in pointer["artifacts"] if f"/{BUILD}/" not in path] + paths
    pointer_path.write_text(json.dumps(pointer, indent=2) + "\n")
    print(json.dumps({"sources": len(SOURCES), "takeaways": sum(len(source["takeaways"]) for source in SOURCES)}))


if __name__ == "__main__":
    main()
