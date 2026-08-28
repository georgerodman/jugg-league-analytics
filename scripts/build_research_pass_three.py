#!/usr/bin/env python3
"""Ingest a broad late-August research pass without regenerating AI summaries."""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = "20260827T170000Z"
BUILT_AT = "2026-08-27T17:00:00Z"
OUT = ROOT / "data/processed/fantasy_analysis" / BUILD
DB = ROOT / ".local/renegade-draft-room.sqlite"
PLAYERS = {name: player_id for player_id, name in sqlite3.connect(DB).execute("SELECT id,display_name FROM players")}


def takeaway(name, label, summary, risks=(), price=None):
    player_id = PLAYERS.get(name)
    if not player_id:
        raise ValueError(f"Unknown player: {name}")
    return {
        "player_id": player_id,
        "player_name": name,
        "label": label,
        "sentiment": "negative" if label in ("avoid", "bust") else "positive",
        "summary": summary,
        "rationale": summary,
        "risks": list(risks),
        "formats": ["redraft", "PPR"],
        "price_condition": price,
        "assumptions": [],
    }


def source(source_id, key, title, author, url, published_at, content_type, summary, rows=()):
    return {
        "id": source_id, "source_key": key, "title": title, "author": author,
        "url": url, "published_at": published_at, "content_type": content_type,
        "summary": summary, "takeaways": list(rows),
    }


SOURCES = [
    source(
        "draftkings:johnson:2026-top-160-aug26", "draftkings_network",
        "2026 Fantasy Football Rankings: Top 160 players for PPR drafts and redraft leagues",
        "Dan Johnson",
        "https://dknetwork.draftkings.com/2026/08/24/2026-fantasy-football-rankings-top-160-players-for-ppr-drafts-and-redraft-leagues/",
        "2026-08-26", "rankings_with_commentary",
        "A price-aware PPR top 160 with explicit target and fade tags plus short editorial notes.",
        [
            takeaway("Jahmyr Gibbs", "target", "Gibbs combines elite rushing efficiency with 77-catch volume, giving him the cleanest overall ceiling even at a top-three price.", ["His acquisition cost leaves almost no room for merely good production."], "Target near ADP 2.8"),
            takeaway("Jonathan Taylor", "target", "Taylor's league-leading rushing workload, efficiency, receiving growth, and goal-line control make a first-round slide especially attractive.", ["His value remains tied to maintaining an unusually heavy workload."], "Strong target beyond ADP 9"),
            takeaway("Christian McCaffrey", "avoid", "McCaffrey's receiving floor remains elite, but 413 touches at age 29 plus recurring soft-tissue trouble make another top-six investment unusually fragile.", ["He can still overcome the workload concern with unmatched receiving production."], "Fade near ADP 6.5"),
            takeaway("Brock Bowers", "target", "Bowers already earns wide-receiver-level route and target volume at fantasy's thinnest position, creating a weekly lineup advantage.", ["The Raiders' offensive ceiling can still limit touchdowns."], "Target around ADP 21"),
            takeaway("Malik Nabers", "value", "Nabers' exceptional target share and healthy-game production offer overall-WR1 volume at a price that already discounts his knee recovery.", ["Medical recovery remains the central uncertainty."], "Target around ADP 28.5"),
            takeaway("A.J. Brown", "value", "Brown remains a proven alpha receiver and moves into an efficient New England passing game prepared to feed him substantial volume.", ["Changing teams introduces role and chemistry uncertainty."], "Target around ADP 20"),
            takeaway("Jaylen Waddle", "value", "Waddle's elite per-route efficiency can finally pair with heavier volume after moving from a low-volume Miami offense to Denver.", ["A new offense and quarterback create transition risk."], "Strong target around ADP 38"),
            takeaway("Ashton Jeanty", "avoid", "Jeanty's ankle sprain, low-efficiency rookie season, and weak scoring environment make his mid-second-round price demanding.", ["His dominant role can still overcome efficiency and team limitations."], "Fade near ADP 15"),
            takeaway("Luther Burden III", "breakout", "Burden's late-season production and exceptional per-route command point to a larger role and meaningful upside beyond his crowded-depth-chart price.", ["The groin injury and target competition can delay the breakout."], "Target around ADP 56"),
            takeaway("Rashee Rice", "avoid", "Rice's short-area volume remains useful, but repeated availability problems make an early-fourth-round price difficult to trust.", ["Healthy games still carry a strong PPR floor."], "Fade near ADP 31"),
            takeaway("Bhayshul Tuten", "target", "Tuten has access to a large vacant workload and valuable scoring opportunities in a productive backfield.", ["His rookie rushing efficiency was poor and the backfield may split more than expected."], "Target around ADP 61"),
            takeaway("Rhamondre Stevenson", "value", "Stevenson's larger playoff snap share and Henderson's pass-protection and ankle issues give him inexpensive access to a substantial role.", ["Henderson can reclaim work when healthy and trusted."], "Target around ADP 83"),
            takeaway("Tyler Warren", "avoid", "Warren's solid rookie volume did not create elite efficiency or touchdown access, making a premium tight-end price hard to justify.", ["Second-year growth could close the gap quickly."], "Strong fade near ADP 44"),
            takeaway("Marvin Harrison Jr.", "value", "Harrison's improving target control and touchdown production offer a post-hype discount on a young receiver with elite draft capital.", ["Injuries and Arizona's passing environment have limited him through two seasons."], "Target around ADP 75"),
            takeaway("Quinshon Judkins", "avoid", "Judkins' weak efficiency and limited receiving production require too many improvements to justify his current fifth-round price.", ["Goal-line volume can preserve weekly usefulness."], "Fade near ADP 54"),
            takeaway("Jaylen Warren", "value", "Warren's receiving role and ability to create yards protect his weekly floor while his price already accounts for early-down competition.", ["Rico Dowdle can cap carries and touchdown chances."], "Target around ADP 80"),
            takeaway("Mike Washington Jr.", "sleeper", "Washington's rare size-speed profile and immediate contingency role behind an injured Ashton Jeanty offer feature-back upside at a near-free price.", ["The role can disappear once Jeanty is healthy."], "Late-round target around ADP 188"),
            takeaway("Woody Marks", "sleeper", "Marks is earning third-down and receiving work in a backfield that may be much closer to a split than his price implies.", ["David Montgomery still projects to control early downs and goal-line work."], "Late target around ADP 178"),
            takeaway("Travis Kelce", "avoid", "Kelce's declining touchdown output and broader target competition make his name value more expensive than younger late-round alternatives.", ["He still led Kansas City in receiving and retains strong chemistry with Mahomes."], "Strong fade near ADP 90"),
        ],
    ),
    source(
        "bleacherreport:buckley:2026-wr-sleepers-busts", "bleacher_report",
        "Fantasy Football 2026 Wide Receiver Sleepers to Draft and Busts to Avoid",
        "Zach Buckley", "https://bleacherreport.com/articles/25470748-fantasy-football-2026-wide-receiver-sleepers-draft-and-busts-avoid",
        "2026-08-14", "sleepers_and_busts",
        "Two receiver sleepers and two price-sensitive avoids.",
        [
            takeaway("De'Zhaun Stribling", "sleeper", "Stribling's explosiveness, second-round investment, and fit in San Francisco's yards-after-catch offense create an immediate path to routes.", ["The veteran receiver room can reduce his role if healthy."], "Late-round sleeper"),
            takeaway("Chris Olave", "avoid", "Olave's third-round price carries more uncertainty than desired because of rookie target competition, quarterback volatility, and injury history.", ["His 2025 volume and production already proved a WR1 ceiling."], "Avoid at a third-round price"),
            takeaway("Rashid Shaheed", "sleeper", "A full offseason in Seattle should create more designed touches for Shaheed's explosive skill set in an offense that may need more passing volume.", ["Seattle failed to integrate him after the trade and the role remains speculative."], "Late-round sleeper"),
            takeaway("Garrett Wilson", "avoid", "Wilson's talent remains clear, but uncertain quarterback improvement and new first-round target competition make his third- or fourth-round ceiling questionable.", ["His historical target dominance can survive a difficult environment."], "Avoid at typical cost"),
        ],
    ),
    source(
        "pff:conway:2026-best-rb-handcuffs", "pff",
        "Fantasy Football 2026: Best running back handcuffs", "Ryan Conway",
        "https://www.pff.com/news/fantasy-football-2026-best-running-back-handcuffs",
        "2026-08-01", "handcuffs",
        "Three backups with credible paths to fantasy relevance if the starter ahead of them misses time.",
        [
            takeaway("Jonathon Brooks", "sleeper", "Brooks can become Carolina's most explosive back if his recovery from consecutive ACL tears restores his college form.", ["He has only nine NFL carries and substantial medical risk."], "Contingent handcuff"),
            takeaway("Blake Corum", "value", "Corum matched Kyren Williams' rushing grade and produced explosive runs on much lower volume, giving him both standalone growth and immediate starter upside if Williams misses time.", ["Williams remains the clear lead back."], "Priority handcuff"),
            takeaway("Jaylen Wright", "sleeper", "Wright becomes fantasy relevant in Miami's run-heavy plan if De'Von Achane misses time, with enough efficiency to handle expanded volume.", ["He played only 127 offensive snaps and fumbled twice on 70 carries."], "Contingent handcuff"),
        ],
    ),
    source(
        "fftoday:krueger:2026-rb-roles-aug24", "fftoday",
        "NFL Running Back Depth Charts & Roles", "Mike Krueger",
        "https://www.fftoday.com/nfl/rb_rooms.html", "2026-08-24", "backfield_roles",
        "A current all-32-team map of lead backs, passing-down and goal-line roles, and projected handcuffs. Stored as contextual depth-chart evidence rather than recommendation votes.",
    ),
    source(
        "draftsharks:smola:2025-target-leaders", "draftsharks",
        "NFL Target Leaders in 2025 (And What It Means For 2026 Fantasy Drafts)", "Jared Smola",
        "https://www.draftsharks.com/article/nfl-target-leaders", "2026-03-06", "usage_leaders",
        "Historical 2025 total targets, target share, and targets-per-route leaders with 2026 interpretation. Stored as objective usage context rather than a blanket positive vote for every leader.",
    ),
    source(
        "statmuse:2025-nfl-touch-leaders", "statmuse",
        "NFL Touch Leaders, 2025", "StatMuse",
        "https://www.statmuse.com/nfl/ask/nfl-touch-leaders-this-season", "2026-06-01", "usage_leaders",
        "Historical 2025 touches, carries, receptions, and targets. Stored as objective workload context and not treated as a player recommendation.",
    ),
    source(
        "pff:mcguinness:2026-offensive-line-rankings", "pff",
        "2026 NFL offensive line rankings", "Gordon McGuinness",
        "https://www.pff.com/news/nfl-offensive-line-rankings-2026", "2026-08-12", "team_context",
        "All 32 offensive lines ranked from multi-year player grades with extra weight on pass protection and tackle play. Stored as team context rather than direct player votes.",
    ),
    source(
        "draftedge:2026-position-schedule-strength-aug24", "draftedge",
        "2026 NFL Team Schedule Strength for Fantasy Football", "DraftEdge",
        "https://fantasy.draftedge.com/nfl-schedule-strength/", "2026-08-24", "schedule_context",
        "Position-specific schedule ratings for every team, with higher ratings representing friendlier fantasy schedules. Stored as contextual evidence rather than direct player votes.",
    ),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paths = []
    for item in SOURCES:
        artifact = {
            "metadata": {"schema_version": 2, "build_id": BUILD, "built_at": BUILT_AT, "season": 2026, "takeaway_count": len(item["takeaways"])},
            "source": {key: item[key] for key in ("id", "source_key", "title", "author", "url", "published_at", "content_type", "summary")} | {"season": 2026},
            "takeaways": item["takeaways"],
        }
        filename = item["id"].replace(":", "_") + ".json"
        (OUT / filename).write_text(json.dumps(artifact, indent=2) + "\n")
        paths.append(f"data/processed/fantasy_analysis/{BUILD}/{filename}")

    pointer_path = ROOT / "data/processed/fantasy_analysis/latest.json"
    pointer = json.loads(pointer_path.read_text())
    existing_urls = set()
    for path in pointer["artifacts"]:
        artifact_path = ROOT / path
        if artifact_path.exists():
            existing_urls.add(json.loads(artifact_path.read_text())["source"]["url"])
    duplicate_urls = [item["url"] for item in SOURCES if item["url"] in existing_urls]
    if duplicate_urls:
        raise ValueError(f"Already ingested URLs: {duplicate_urls}")
    pointer["artifacts"] += paths
    pointer_path.write_text(json.dumps(pointer, indent=2) + "\n")
    print(json.dumps({"sources": len(SOURCES), "takeaways": sum(len(item["takeaways"]) for item in SOURCES)}))


if __name__ == "__main__":
    main()
