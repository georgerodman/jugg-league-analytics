#!/usr/bin/env python3
"""Ingest supplied August 2026 RotoWire research without refreshing AI summaries."""
import csv,hashlib,json,sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];DOWNLOADS=Path("/Users/george.rodman/Downloads")
BUILD="20260827T150000Z";BUILT_AT="2026-08-27T15:00:00Z"
ANALYSIS=ROOT/"data/processed/fantasy_analysis"/BUILD;CONTEXT=ROOT/"data/processed/fantasy_context"/BUILD
PLAYERS={name:pid for pid,name in sqlite3.connect(ROOT/".local/renegade-draft-room.sqlite").execute("SELECT id,display_name FROM players")}
FILES={
"waiver":DOWNLOADS/"Top Fantasy Football Waiver Wire Pickups_ Preseason Pickups & Late-Round Targets _ RotoWire.pdf",
"sleepers":DOWNLOADS/"Fantasy Football Sleepers 2026_ 5 Underrated Running Backs to Target _ RotoWire.pdf",
"busts":DOWNLOADS/"Fantasy Football Busts 2026_ 5 Overrated Running Backs to Fade _ RotoWire.pdf",
"best_ball":DOWNLOADS/"2026 Best Ball Strategy_ Market Overreactions _ RotoWire.pdf",
"guillotine":DOWNLOADS/"Guillotine, Chopped and Knockout Leagues_ 3 TEs to Target, 3 TEs to Avoid _ RotoWire.pdf",
"comparison":DOWNLOADS/"Who Should I Draft_ CeeDee Lamb vs Justin Jefferson _ RotoWire.pdf",
"bust_rates":DOWNLOADS/"First Round Busts_ NFL Fantasy Bust_Breakout Rates _ RotoWire.pdf",
"wr_adp":DOWNLOADS/"Fantasy Football ADP Analysis 2026_ Undervalued & Overvalued Wide Receivers _ RotoWire.pdf",
"cheat_sheet":DOWNLOADS/"2026 Fantasy Football Cheat Sheet _ RotoWire.pdf",
"auction":DOWNLOADS/"auction-values-ALL.csv","excluded":DOWNLOADS/"pick.csv"}

def t(name,label,summary,risk,price=None,formats=("redraft",)):
    if name not in PLAYERS:raise ValueError(f"Unknown player {name}")
    return {"player_id":PLAYERS[name],"player_name":name,"label":label,"sentiment":"negative" if label in ("avoid","bust") else "positive","summary":summary,"rationale":summary,"risks":[risk],"formats":list(formats),"price_condition":price,"assumptions":[]}

def s(sid,title,author,url,date,kind,summary,rows=()):return {"id":sid,"source_key":"rotowire","title":title,"author":author,"url":url,"published_at":date,"content_type":kind,"summary":summary,"takeaways":list(rows)}

SOURCES=[
s("rotowire:bartel:2026-preseason-waiver-targets","Fantasy Football Waiver Wire: Preseason Pickups & Late-Round Targets","Joe Bartel","https://www.rotowire.com/football/article/fantasy-football-waiver-wire-preseason-pickups-late-round-targets-129698","2026-08-24","waiver_and_late_round_targets","Preseason waiver and late-round recommendations with format and FAAB context",[
t("Malik Willis","sleeper","Rushing and an inviting opener offer low-end QB1 upside mainly in two-QB or deep formats.","Miami's passing ceiling is low.","Deep leagues; 0% FAAB",("deep_redraft","superflex")),
t("Mike Washington Jr.","value","He is the immediate Jeanty contingency with attractive size and speed, but the injury news reduces urgency.","Las Vegas may add a veteran and Jeanty's injury is not long term.","5% FAAB"),
t("Tyler Allgeier","value","Early volume and goal-line work while Jeremiyah Love recovers are underpriced.","Arizona may create few scoring chances and Love can reclaim work.","4% FAAB"),
t("MarShawn Lloyd","sleeper","He remains a valuable Josh Jacobs handcuff with complementary explosiveness.","Extensive injuries and pass-protection competition cap standalone work.","1% FAAB",("deep_redraft",)),
t("Kaelon Black","sleeper","First-team preseason work makes him a speculative McCaffrey contingency.","The backup role remains unsettled.","Monitor only",("deep_redraft",)),
t("Demond Claiborne","sleeper","Elite speed offers contingent splash-play appeal behind Aaron Jones and Jordan Mason.","He may open with only a return role.","Deep lottery ticket",("deep_redraft",)),
t("Dontayvion Wicks","sleeper","A strong camp and Philadelphia's trade investment give him runway as the starter opposite DeVonta Smith.","The offense is run-heavy and receiver competition remains.","2% FAAB"),
t("Caleb Douglas","sleeper","Chris Bell's recovery opens early routes for a toolsy third-round rookie.","Miami may not support a useful receiver.","Deep leagues",("deep_redraft",)),
t("Jaylin Noel","sleeper","Houston's injuries create a path to the primary slot role.","His own hamstring injury clouds the opening opportunity.","Deep benches",("deep_redraft",)),
t("Chig Okonkwo","sleeper","Athleticism, a proven reception floor and growing rapport with Jayden Daniels create breakout potential.","Diggs and McLaurin remain ahead in the target order.","3% FAAB"),
t("Greg Dulcich","sleeper","He can become Malik Willis' preferred middle-of-field target at no cost.","The offense has a weak passing ceiling.","Deep leagues",("deep_redraft",))]),
s("rotowire:mckechnie:2026-rb-sleepers-aug27","2026 Fantasy Football Sleepers: 5 Underrated Running Backs to Target","John McKechnie","https://www.rotowire.com/football/article/2026-fantasy-football-sleepers-five-underrated-running-backs-to-target-129827","2026-08-27","rb_sleepers","Five primary values plus deep contingent backs",[
t("Travis Etienne Jr.","value","A clear lead role, proven volume and receiving ability create upper-RB2 value while Kamara recovers.","The fourth-round price is value rather than a classic sleeper price.","ADP 43.9 / RB18"),
t("Tyler Allgeier","sleeper","Early volume and short-yardage work can create flex weeks even after Love returns.","The ceiling and scoring environment are modest.","ADP 148.5 / RB45"),
t("Jordan Mason","sleeper","Strong rushing efficiency and a better Minnesota offense create standalone and contingent upside.","Aaron Jones still leads the depth chart and Mason's sample is smaller.","ADP 123.1 / RB40"),
t("Chris Rodriguez Jr.","sleeper","Power, after-contact production and likely goal-line work are underpriced.","Tuten and LeQuint Allen can control other valuable roles.","ADP 147.2 / RB43"),
t("Dylan Sampson","sleeper","Target-earning efficiency and a checkdown-heavy offense create a path to 50 catches.","The thesis is much weaker outside full PPR.","ADP 173.9 / RB49",("PPR",)),
t("Sean Tucker","sleeper","Demonstrated spike-week upside makes him a worthwhile final-round contingency.","He likely needs an injury ahead of him.","Final rounds",("deep_redraft","best_ball")),
t("Demond Claiborne","sleeper","His 4.37 speed offers a small chance of usable splash weeks.","He may have no offensive role.","Final rounds",("deep_redraft","best_ball")),
t("Emmett Johnson","sleeper","Kansas City's likely No. 2 back carries contingent upside and possible standalone work.","Kenneth Walker controls the backfield while healthy.","Final rounds",("deep_redraft","best_ball"))]),
s("rotowire:coventry:2026-rb-busts-aug25","2026 Fantasy Football Busts: 5 Overrated Running Backs to Fade","Jim Coventry","https://www.rotowire.com/football/article/2026-fantasy-football-busts-four-overrated-running-backs-to-fade-130011","2026-08-25","rb_busts","Five backs whose prices understate workload, efficiency or role risk",[
t("Christian McCaffrey","bust","An RB3 price captures last year's 413-touch ceiling while discounting efficiency decline and accumulated wear.","Elite receiving volume still supplies a stable floor.","ADP 8 / RB3"),
t("Kenneth Walker III","bust","A workhorse price assumes a workload he has never handled and overlooks boom-or-bust rushing efficiency.","Kansas City's investment and scoring environment preserve upside.","ADP 15 / RB9"),
t("Breece Hall","bust","Aaron Glenn's committee preference and Braelon Allen's high-value roles cap Hall's ceiling.","Hall remains the most talented back and has a major contract.","ADP 39 / RB16"),
t("TreVeyon Henderson","bust","He is priced as the leader even though Rhamondre Stevenson controlled the postseason workload.","Henderson's 2025 production preserves a meaningful ceiling.","ADP 58 / RB22"),
t("Bhayshul Tuten","bust","Poor rookie efficiency plus separate goal-line and receiving specialists leave few high-value touches.","His speed still creates rotational upside.","ADP 59 / RB23")]),
s("rotowire:coventry:2026-wr-adp-aug26","2026 Fantasy Football ADP Analysis: Undervalued & Overvalued Wide Receivers","Jim Coventry","https://www.rotowire.com/football/article/2026-fantasy-football-adp-analysis-undervalued-overvalued-wide-receivers-130080","2026-08-26","wr_values_and_fades","Three receiver values and two fades",[
t("DJ Moore","value","A clear No. 1 role with Josh Allen, little competition and a strong improvisational fit are underpriced.","Buffalo's target distribution can remain volatile.","WR22"),
t("Marvin Harrison Jr.","value","A motion and play-action system should manufacture easier separation and after-catch chances.","Health and drops remain concerns.","WR32"),
t("Chris Godwin Jr.","value","A healthy offseason and proven Mayfield chemistry offer lead-receiver production at a discounted price.","Age, prior injuries and Egbuka create downside.","WR34"),
t("Jameson Williams","bust","Recent production relied on teammate absences or extreme scripts, while line uncertainty threatens deep volume.","Explosive ability still supports spike weeks.","WR24"),
t("Davante Adams","bust","Age, hamstring trouble, shrinking volume and more multi-TE personnel threaten touchdown regression.","Stafford chemistry remains a positive.","WR28")]),
s("rotowire:huntington:2026-lamb-vs-jefferson","Who Should I Draft: CeeDee Lamb vs Justin Jefferson","Tyler Huntington","https://www.rotowire.com/football/article/who-should-i-draft-ceedee-lamb-vs-justin-jefferson-2026-fantasy-football-130048","2026-08-26","player_comparison","Half-PPR comparison where the projections favor Lamb and the final personal preference is Jefferson",[
t("CeeDee Lamb","target","He owns the stronger projected points, floor, ceiling and target volume in this elite comparison.","The edge is modest and both carry first-round prices.","WR5",("half_PPR","PPR","standard")),
t("Justin Jefferson","target","Elite talent and Kevin O'Connell upside can justify choosing him over Lamb's slightly stronger projection.","His projected floor, ceiling and volume trail Lamb slightly.","WR6",("half_PPR","PPR","standard"))]),
s("rotowire:mckechnie:2026-best-ball-overreactions","2026 Best Ball Strategy: Market Overreactions","John McKechnie","https://www.rotowire.com/football/article/2026-best-ball-strategy-market-overreactions-130014","2026-08-25","format_specific_context","Best-ball opinions retained as context rather than redraft votes"),
s("rotowire:bulanda:2026-guillotine-tight-ends","2026 Guillotine League Draft Strategy: 3 TEs to Target, 3 TEs to Avoid","Steve Bulanda","https://www.rotowire.com/football/article/2026-guillotine-league-draft-strategy-3-tes-to-target-3-tes-to-avoid-130015","2026-08-25","format_specific_context","Early-survival tight-end opinions retained as guillotine context rather than redraft votes"),
s("rotowire:huntington:2015-2025-bust-rates","First Round Busts: What 11 Years of Fantasy Football Drafts Say About First Round Bust Rates","Tyler Huntington","https://www.rotowire.com/football/article/first-round-busts-what-11-years-of-fantasy-football-drafts-say-about-first-round-bust-rates-130067","2026-08-26","draft_strategy_context","Historical ADP outcome study retained as strategy context"),
s("rotowire:2026-cheat-sheet-aug27","2026 Fantasy Football Cheat Sheet","RotoWire Staff","https://www.rotowire.com/football/cheatsheet.php","2026-08-27","rankings_context","Overall 2026 rankings and bye-week cheat sheet"),
s("rotowire:2026-auction-values-export-aug27","2026 Fantasy Football Auction Values Export","RotoWire Staff","https://www.rotowire.com/football/auction-values.php","2026-08-27","auction_value_context","Auction values and projections with undocumented export assumptions; not JUGG prices")]

FORMAT_NOTES=[
("Chuba Hubbard","best_ball","positive","A fall beyond pick 100 makes his shared role acceptable, though Carolina remains a weak environment.","Brooks can win more work."),
("Oronde Gadsden II","best_ball","mixed","A massive ADP fall creates a last-round rebound case, but preseason usage and added veterans are bearish.","He may be third in the tight-end rotation."),
("Cam Ward","best_ball","negative","Poor preseason play and a likely bottom-three offense make the market downgrade look justified.","Preseason results are noisy."),
("Dallas Goedert","guillotine","positive","Vacated targets and a safe role create an early-survival value.","This is not a full-season ceiling call."),
("Juwan Johnson","guillotine","positive","A likely No. 2 role and touchdown rebound potential make him an inexpensive survival option.","The case partly depends on Tyson's absence."),
("Dalton Schultz","guillotine","positive","Receiver injuries and a favorable early schedule create a safe late option.","The edge is concentrated early."),
("Tucker Kraft","guillotine","negative","A possible early snap cap after ACL surgery makes TE5 too risky for elimination.","Full-season ability remains strong."),
("Sam LaPorta","guillotine","negative","Back and hip concerns, a crowded target tree and an early bye weaken survival value.","Healthy spike-week upside remains."),
("George Kittle","guillotine","negative","A top-10 price seven months after an Achilles tear is too risky for early survival.","An unusually fast recovery could beat the concern.")]
FORMAT_NOTES=[{"player":p,"format":f,"sentiment":sent,"summary":sm,"risks":[risk],"source_id":"rotowire:mckechnie:2026-best-ball-overreactions" if f=="best_ball" else "rotowire:bulanda:2026-guillotine-tight-ends"} for p,f,sent,sm,risk in FORMAT_NOTES]

def auction_rows():
    with FILES["auction"].open(encoding="utf-8-sig",newline="") as stream:
        next(stream);rows=[]
        for row in csv.DictReader(stream):
            if not row.get("Name"):continue
            num=lambda key,kind:kind(row[key]) if row.get(key) else None
            rows.append({"player":row["Name"],"team":row.get("Team"),"position":row.get("Pos"),"bye":num("BYE",int),"auction_value":num("Value",float),"overall_rank":num("Rank",int),"projected_points":num("Pts",float),"consensus_rank":num("Consensus",int),"assumptions":"Scoring, roster, team-count and budget assumptions were not included in the supplied export."})
        return rows

def main():
    for path in FILES.values():
        if not path.exists():raise FileNotFoundError(path)
    if "Jusuf Nurkic" not in FILES["excluded"].read_text(encoding="utf-8-sig"):raise ValueError("Unreviewed pick.csv")
    ANALYSIS.mkdir(parents=True,exist_ok=True);CONTEXT.mkdir(parents=True,exist_ok=True);paths=[]
    for item in SOURCES:
        artifact={"metadata":{"schema_version":2,"build_id":BUILD,"built_at":BUILT_AT,"season":2026,"takeaway_count":len(item["takeaways"])},"source":{k:item[k] for k in ("id","source_key","title","author","url","published_at","content_type","summary")}|{"season":2026},"takeaways":item["takeaways"]}
        fn=item["id"].replace(":","_")+".json";(ANALYSIS/fn).write_text(json.dumps(artifact,indent=2)+"\n");paths.append(str((ANALYSIS/fn).relative_to(ROOT)))
    pointer_path=ROOT/"data/processed/fantasy_analysis/latest.json";pointer=json.loads(pointer_path.read_text())
    urls={json.loads((ROOT/p).read_text())["source"]["url"] for p in pointer["artifacts"] if (ROOT/p).exists()}
    dup=[x["url"] for x in SOURCES if x["url"] in urls]
    if dup:raise ValueError(f"Already ingested URLs: {dup}")
    pointer["artifacts"]+=paths;pointer_path.write_text(json.dumps(pointer,indent=2)+"\n")
    oldp=json.loads((ROOT/"data/processed/fantasy_context/latest.json").read_text());context=json.loads((ROOT/oldp["artifact"]).read_text())
    context["metadata"]={"schema_version":2,"build_id":BUILD,"built_at":BUILT_AT}
    context["datasets"]["rotowire_auction_values_2026"]={"source_id":"rotowire:2026-auction-values-export-aug27","rows":auction_rows()}
    context["datasets"]["rotowire_format_specific_notes_2026"]={"source_ids":sorted({r["source_id"] for r in FORMAT_NOTES}),"rows":FORMAT_NOTES}
    context["datasets"]["rotowire_draft_strategy_2015_2025"]={"source_id":"rotowire:huntington:2015-2025-bust-rates","rows":[{"sample_picks":1699,"seasons":"2015-2025","first_round_bust_or_miss_rate":"52%","round_6_rb_bust_rate":"2%","round_6_rb_league_winner_rate":"18%","notes":"Historical strategy context, not a player recommendation or deterministic forecast."}]}
    context.setdefault("source_files",{}).update({k:{"path":str(v),"sha256":hashlib.sha256(v.read_bytes()).hexdigest()} for k,v in FILES.items() if k!="excluded"})
    cp=CONTEXT/"rotowire_august_context.json";cp.write_text(json.dumps(context,indent=2)+"\n");(ROOT/"data/processed/fantasy_context/latest.json").write_text(json.dumps({"schema_version":2,"artifact":str(cp.relative_to(ROOT))},indent=2)+"\n")
    print(json.dumps({"sources":len(SOURCES),"takeaways":sum(len(x["takeaways"]) for x in SOURCES),"auction_rows":len(context["datasets"]["rotowire_auction_values_2026"]["rows"]),"format_notes":len(FORMAT_NOTES),"excluded":["pick.csv (NBA)"]}))

if __name__=="__main__":main()
