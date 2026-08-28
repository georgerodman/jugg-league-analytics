#!/usr/bin/env python3
"""Build cached AI player syntheses and the offline fantasy research brief."""

import hashlib,json,os,re,sqlite3,time,urllib.request
from collections import defaultdict
from datetime import datetime,timezone
from html import escape
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROMPT_VERSION="fantasy-player-synthesis-v10-interpreted-stats"
BUILD_ID=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT=ROOT/"data/processed/fantasy_research"/BUILD_ID
REPORT_MD=ROOT/"output/reports/2026-fantasy-research-brief.md"
REPORT_PDF=ROOT/"output/pdf/2026-fantasy-research-brief.pdf"

def load_env():
    env=ROOT/".env"
    if not env.exists():return
    for line in env.read_text().splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:continue
        key,value=line.split("=",1);os.environ.setdefault(key.strip(),value.strip().strip('"').strip("'"))

def evidence():
    pointer=json.loads((ROOT/"data/processed/fantasy_analysis/latest.json").read_text());grouped=defaultdict(list);sources={}
    for relative in pointer["artifacts"]:
        artifact=json.loads((ROOT/relative).read_text());source=artifact["source"];sources[source["id"]]=source
        for row in artifact["takeaways"]:
            grouped[row["player_id"]].append({**row,"source_id":source["id"],"publication":source["source_key"],"source_title":source["title"],"author":source.get("author"),"url":source["url"],"published_at":source["published_at"],"content_type":source["content_type"]})
    return grouped,sources

def opinion_counts(rows):
    latest={}
    for row in sorted(rows,key=lambda r:r["published_at"],reverse=True):latest.setdefault((row.get("author") or row["source_id"]).lower(),row)
    values=list(latest.values());return sum(r["sentiment"]=="positive" for r in values),sum(r["sentiment"]=="negative" for r in values),len(values)

def action(rows):
    positive,negative,_=opinion_counts(rows)
    return "Target" if positive>negative else "Avoid" if negative>positive else None

TEAM_NAMES={"ARI":"Arizona Cardinals","ATL":"Atlanta Falcons","BAL":"Baltimore Ravens","BUF":"Buffalo Bills","CAR":"Carolina Panthers","CHI":"Chicago Bears","CIN":"Cincinnati Bengals","CLE":"Cleveland Browns","DAL":"Dallas Cowboys","DEN":"Denver Broncos","DET":"Detroit Lions","GB":"Green Bay Packers","HOU":"Houston Texans","IND":"Indianapolis Colts","JAX":"Jacksonville Jaguars","KC":"Kansas City Chiefs","LAC":"Los Angeles Chargers","LAR":"Los Angeles Rams","LV":"Las Vegas Raiders","MIA":"Miami Dolphins","MIN":"Minnesota Vikings","NE":"New England Patriots","NO":"New Orleans Saints","NYG":"New York Giants","NYJ":"New York Jets","PHI":"Philadelphia Eagles","PIT":"Pittsburgh Steelers","SEA":"Seattle Seahawks","SF":"San Francisco 49ers","TB":"Tampa Bay Buccaneers","TEN":"Tennessee Titans","WAS":"Washington Commanders"}
OL_ORDER=["DEN","PHI","TB","IND","CHI","BUF","LAC","KC","ATL","SF","LAR","MIN","NE","PIT","SEA","NO","DAL","LV","DET","CIN","NYJ","ARI","NYG","BAL","MIA","CAR","HOU","GB","TEN","JAX","CLE","WAS"]
OL_RANK={team:index+1 for index,team in enumerate(OL_ORDER)}
SCHEDULE={
"MIN":(5,4,5,4),"DET":(5,5,4,3),"PHI":(5,4,4,4),"IND":(4,4,4,3),"HOU":(4,4,3,4),"NYG":(4,4,4,3),"NYJ":(4,3,4,4),"GB":(4,4,5,2),"JAX":(4,4,4,3),"SEA":(4,4,3,3),"MIA":(3,3,3,5),"BAL":(3,3,4,4),"LAR":(3,5,1,4),"CLE":(4,3,3,3),"ATL":(4,2,3,3),"CIN":(3,2,4,3),"BUF":(3,2,4,3),"TEN":(3,3,3,3),"LAC":(2,3,2,4),"KC":(2,3,2,4),"NO":(3,3,3,2),"DEN":(3,2,2,4),"DAL":(2,4,2,2),"NE":(2,2,2,4),"TB":(2,2,4,2),"CHI":(3,2,3,2),"WAS":(2,4,2,1),"PIT":(2,2,3,2),"SF":(1,2,2,3),"LV":(1,2,2,3),"ARI":(None,2,2,2),"CAR":(2,1,2,2)}

def contextual_evidence():
    pointer=ROOT/"data/processed/fantasy_context/latest.json"
    context=json.loads((ROOT/json.loads(pointer.read_text())["artifact"]).read_text())["datasets"]
    targets={row["player"]:row for row in context["player_targets_2025"]["rows"]}
    team_targets={row["team"]:row for row in context["team_targets_2025"]["rows"]}
    handcuffs={row["team"]:row for row in context["rb_handcuffs_2026"]["rows"]}
    db=sqlite3.connect(ROOT/".local/renegade-draft-room.sqlite")
    profiles={row[0]:{"name":row[1],"position":row[2],"team":row[3]} for row in db.execute("SELECT id,display_name,position,nfl_team FROM players")}
    fantasypros={}
    fp_pointer=ROOT/"data/processed/fantasypros_context/2026/latest.json"
    if fp_pointer.exists():
        pointer_payload=json.loads(fp_pointer.read_text())
        artifact=json.loads((ROOT/pointer_payload["artifact"]).read_text())
        snapshot=artifact["metadata"]["snapshot_id"]
        retrieved_at=artifact["metadata"]["retrieved_at"]
        fantasypros={row["internal_player_id"]:{**row,"snapshot_id":snapshot,"retrieved_at":retrieved_at} for row in artifact["ai_player_context"]}
    format_notes={}
    for row in context.get("rotowire_format_specific_notes_2026",{}).get("rows",[]):format_notes.setdefault(row["player"],[]).append(row)
    auction={row["player"]:row for row in context.get("rotowire_auction_values_2026",{}).get("rows",[])}
    return profiles,targets,team_targets,handcuffs,fantasypros,format_notes,auction

def player_context(player_id,profiles,targets,team_targets,handcuffs,fantasypros,format_notes,auction):
    profile=profiles.get(player_id,{})
    name,position,team=profile.get("name"),profile.get("position"),profile.get("team")
    facts=[];source_ids=[]
    usage=targets.get(name)
    if usage:
        facts.append({"type":"historical_usage","text":f"2025: {usage['targets']} targets ({usage['targets_per_game']} per game). This is prior-season usage, not a 2026 projection."})
        source_ids.append("fantasypros:pdf:player_targets:2026-08-26")
    if team in OL_RANK:
        rank=OL_RANK[team];band="strong" if rank<=10 else "middle" if rank<=22 else "weak"
        facts.append({"type":"offensive_line","text":f"Current team offensive line ranks {rank} of 32 ({band} tier) in PFF's 2026 preseason ranking."})
        source_ids.append("pff:mcguinness:2026-offensive-line-rankings")
    if team in SCHEDULE and position in ("QB","RB","WR","TE"):
        rating=SCHEDULE[team][("QB","RB","WR","TE").index(position)]
        if rating is not None:
            meaning={1:"very difficult",2:"difficult",3:"neutral",4:"favorable",5:"very favorable"}[rating]
            facts.append({"type":"schedule","text":f"2026 {position} schedule rating is {rating}/5 ({meaning}); 5 is friendliest and 1 is hardest. Treat preseason schedule strength as a modest tiebreaker, not a primary projection."})
            source_ids.append("draftedge:2026-position-schedule-strength-aug24")
    team_row=team_targets.get(TEAM_NAMES.get(team))
    if team_row and position in ("RB","WR","TE"):
        prefix=position.lower();facts.append({"type":"team_usage","text":f"This franchise's 2025 {position} group received {team_row[prefix+'_targets']} targets, a {team_row[prefix+'_share']} positional share. Personnel and scheme may have changed for 2026."})
        source_ids.append("fantasypros:pdf:team_targets:2026-08-26")
    cuff=handcuffs.get(TEAM_NAMES.get(team))
    if position=="RB" and cuff and name in (cuff.get("projected_starter"),cuff.get("handcuff")):
        role="projected starter" if name==cuff.get("projected_starter") else f"primary handcuff behind {cuff.get('projected_starter')}"
        facts.append({"type":"backfield_role","text":f"FantasyPros lists this player as the {role}; depth-chart labels are contingent context, not recommendation votes."})
        source_ids.append("fantasypros:pdf:rb_handcuffs:2026-08-26")
    current=fantasypros.get(player_id)
    if current:
        snapshot=current["snapshot_id"]
        ranking=current.get("ranking")
        if ranking:
            spread=f"; expert range {ranking['rank_best']}-{ranking['rank_worst']}" if ranking.get("rank_best") and ranking.get("rank_worst") else ""
            facts.append({"type":"consensus_ranking","as_of":current["retrieved_at"],"text":f"FantasyPros 2026 non-PPR expert consensus ranks this player {ranking.get('position_rank') or ranking.get('ecr')} (tier {ranking.get('tier')}){spread}. This is current market/analyst context, not a projection, auction value, or player vote."})
            source_ids.append(f"fantasypros:api:consensus-rankings:{snapshot}")
        injury=current.get("injury")
        if injury:
            details=[injury.get("status"),injury.get("injury_type"),injury.get("comment")]
            facts.append({"type":"current_injury","as_of":injury.get("injury_update_date") or current["retrieved_at"],"text":"FantasyPros injury report: "+"; ".join(str(value) for value in details if value)+". This is volatile availability context and must be described with its date."})
            source_ids.append(f"fantasypros:api:injuries:{snapshot}")
        for news in current.get("recent_news",[])[:3]:
            detail=" ".join(value for value in (news.get("description"),news.get("impact")) if value)
            facts.append({"type":"current_news","as_of":news.get("created_at") or current["retrieved_at"],"text":f"{news.get('title')}. {detail}".strip()})
            source_ids.append(f"fantasypros:api:news:{snapshot}")
    market=auction.get(name)
    if market:
        facts.append({"type":"external_market_context","text":f"RotoWire export: overall rank {market.get('overall_rank')}, projected points {market.get('projected_points')}, and auction value {market.get('auction_value')}. The export omitted scoring, roster, team-count, and budget assumptions, so do not compare this dollar value directly with JUGG xPRICE."})
        source_ids.append("rotowire:2026-auction-values-export-aug27")
    for note in format_notes.get(name,[]):
        facts.append({"type":"format_specific_opinion","format":note["format"],"sentiment":note["sentiment"],"text":note["summary"],"risks":note["risks"]})
        source_ids.append(note["source_id"])
    return facts,sorted(set(source_ids))

def input_record(player_id,rows,profiles,targets,team_targets,handcuffs,fantasypros,format_notes,auction):
    compact=[{"source_id":r["source_id"],"publication":r["publication"],"author":r.get("author"),"date":r["published_at"],"label":r["label"],"sentiment":r["sentiment"],"summary":r["summary"],"rationale":r["rationale"],"risks":r["risks"],"formats":r.get("formats",[]),"price_condition":r.get("price_condition"),"assumptions":r.get("assumptions",[])} for r in rows]
    context,context_source_ids=player_context(player_id,profiles,targets,team_targets,handcuffs,fantasypros,format_notes,auction)
    canonical=json.dumps({"opinions":compact,"context":context},sort_keys=True,separators=(",",":"));return {"player_id":player_id,"player_name":rows[0]["player_name"],"evidence":compact,"context":context,"context_source_ids":context_source_ids,"input_hash":hashlib.sha256(canonical.encode()).hexdigest()}

def response_text(payload):
    if isinstance(payload.get("output_text"),str):return payload["output_text"]
    return "".join(item.get("text","") for output in payload.get("output",[]) for item in output.get("content",[]) if item.get("type") in ("output_text","text"))

def synthesize(records,model):
    key=os.environ.get("OPENAI_API_KEY");
    if not key:raise RuntimeError("OPENAI_API_KEY is required to generate AI research summaries")
    results={}
    schema={"type":"object","properties":{"summaries":{"type":"array","items":{"type":"object","properties":{"player_id":{"type":"string"},"card_summary":{"type":"string"},"full_writeup":{"type":"string"}},"required":["player_id","card_summary","full_writeup"],"additionalProperties":False}}},"required":["summaries"],"additionalProperties":False}
    batch_size=5
    for start in range(0,len(records),batch_size):
        batch=records[start:start+batch_size]
        instructions="You synthesize supplied fantasy-football research only. For each player, produce two distinct outputs. CARD SUMMARY: one or two concise sentences for a draft-night player card; state the overall interpretation and main rationale, then the most meaningful concern, disagreement, assumption, format, price, schedule, usage, or team-environment dependency. FULL WRITEUP: exactly two short paragraphs, normally 100-200 words total when the material supports it. The first paragraph contains the player's Pros: the strongest favorable football case and what is working in his favor. The second contains the player's Cons: the clearest weaknesses, risks, price sensitivity, role or injury assumptions, and meaningful disagreement. Do not add Pros or Cons headings because the interface supplies them. Write in a natural, confident fantasy-football voice and present the assessment directly. The context facts are supporting inputs, not positive or negative votes: use only facts genuinely relevant to the player's case, treat preseason schedule as a modest tiebreaker, distinguish 2025 usage from 2026 expectations, and do not force every context item into the prose. Never cite a raw statistic unless you can also explain whether it is strong, weak, unusual, improving, declining, or otherwise meaningful using a supplied rank, percentile, league or position benchmark, trend, or clear football implication. If the inputs do not establish that interpretation, omit the statistic rather than making the reader interpret an isolated number. Treat consensus rankings as non-PPR market/analyst context, never as projections or auction prices. Injury and news items are volatile dated facts: preserve their time framing, acknowledge conflicts, and never turn an old item into a current claim. Do not name analysts or publications. Do not use meta-language about the inputs, such as 'the analyst says,' 'the article argues,' 'the supplied evidence,' 'the supplied evaluations suggest,' 'the evidence suggests,' 'the research indicates,' or similar framing. When opinions conflict, explain the competing football cases directly; never attribute either side by name. Attribution is displayed separately. When support is thin, be appropriately restrained without talking about source quantity or quality. Do not add outside facts. Do not mention data structures. Do not claim consensus when only one independent analyst is present. Do not use Watch as a classification; a tied or unresolved action is simply no Target/Avoid lean. Do not pad the full writeup with generic caveats."
        request={"model":model,"instructions":instructions,"input":json.dumps([{"player_id":r["player_id"],"player_name":r["player_name"],"opinions":r["evidence"],"context":r["context"]} for r in batch]),"max_output_tokens":5000,"store":False,"text":{"verbosity":"low","format":{"type":"json_schema","name":"player_summaries","strict":True,"schema":schema}}}
        req=urllib.request.Request("https://api.openai.com/v1/responses",data=json.dumps(request).encode(),headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(req,timeout=120) as response:parsed=json.loads(response.read())
        decoded=json.loads(response_text(parsed));results.update({row["player_id"]:{"card_summary":row["card_summary"].strip(),"full_writeup":row["full_writeup"].strip()} for row in decoded["summaries"]});print(f"AI summaries: {min(start+batch_size,len(records))}/{len(records)}",flush=True);time.sleep(.15)
    return results

def markdown(grouped,summaries,sources):
    rows=[]
    for player_id,evidence_rows in grouped.items():
        positive,negative,count=opinion_counts(evidence_rows);tags=sorted({r["label"].title() for r in evidence_rows if r["label"] in ("sleeper","breakout","value","bust")})
        rows.append({"id":player_id,"name":evidence_rows[0]["player_name"],"action":action(evidence_rows),"positive":positive,"negative":negative,"count":count,"tags":tags,"full_writeup":summaries[player_id]["full_writeup"],"sources":sorted({r["source_id"] for r in evidence_rows}),"price":next((r.get("price_condition") for r in evidence_rows if r.get("price_condition")),None)})
    targets=sorted((r for r in rows if r["action"]=="Target"),key=lambda r:(-r["count"],-r["positive"],r["name"]));avoids=sorted((r for r in rows if r["action"]=="Avoid"),key=lambda r:(-r["count"],-r["negative"],r["name"]));divisive=sorted((r for r in rows if r["positive"] and r["negative"]),key=lambda r:(-r["count"],r["name"]));
    def section(title,items,limit=18):
        lines=[f"## {title}",""]
        for row in items[:limit]:
            meta=f"{row['positive']} positive, {row['negative']} negative; {row['count']} independent analyst{'s' if row['count']!=1 else ''}";tag=f" Tags: {', '.join(row['tags'])}." if row["tags"] else "";price=f" Price context: {row['price']}." if row["price"] else ""
            lines += [f"### {row['name']}","",f"**{row['action']} - {meta}.**{tag}{price}","",row["full_writeup"],""]
        return lines
    lines=["# 2026 Fantasy Football Research Brief","",f"Generated {datetime.now().strftime('%B %d, %Y')} from {len(sources)} retained articles and {sum(len(v) for v in grouped.values())} structured player takeaways.","","> League lens: 10-team, non-PPR auction. Source articles using PPR, dynasty, deep-league, or superflex assumptions are identified in the underlying evidence and treated cautiously.","","## Executive summary","",f"The library currently covers {len(rows)} players. It produces {len(targets)} Target leans, {len(avoids)} Avoid leans, and {len(rows)-len(targets)-len(avoids)} players with no automatic action before manual overrides.","","The strongest conclusions are the players supported or opposed by several independent analysts. A one-source recommendation is useful evidence, but it is not described as broad consensus.",""]
    lines+=section("Strongest targets",targets)
    lines+=section("Players to avoid at current price",avoids)
    lines+=section("Most divisive players",divisive,20)
    for tag,title in [("Sleeper","Sleepers and late-round targets"),("Value","Best values"),("Breakout","Breakout candidates"),("Bust","Bust concerns")]:lines+=section(title,sorted((r for r in rows if tag in r["tags"]),key=lambda r:(-r["count"],r["name"])),15)
    lines += ["## Source guide",""]
    for source in sorted(sources.values(),key=lambda s:(s["source_key"],s["published_at"],s["title"])):lines.append(f"- [{source['title']}]({source['url']}) - {source.get('author') or 'Staff'}, {source['published_at']} ({source['source_key']})")
    lines += ["","## Methodology", "", "Player votes are deduplicated by analyst, using the newest retained opinion for the deterministic positive/negative split. Target and Avoid are the only action signals; a tie produces no automatic action. Sleeper, Breakout, Value, and Bust are descriptive tags. Card summaries and full writeups combine retained player takeaways with applicable historical usage, backfield-role, schedule, and offensive-line context, and are cached by an input hash and prompt version. Context never creates a player vote by itself. Manual overrides in the application affect the displayed flag only.",""]
    return "\n".join(lines)

def pdf_from_markdown(text):
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,KeepTogether
    REPORT_PDF.parent.mkdir(parents=True,exist_ok=True);styles=getSampleStyleSheet();styles.add(ParagraphStyle(name="Title2",parent=styles["Title"],fontName="Helvetica-Bold",fontSize=22,leading=27,textColor=HexColor("#183746"),spaceAfter=16,alignment=TA_CENTER));styles.add(ParagraphStyle(name="H2x",parent=styles["Heading2"],fontSize=15,leading=19,textColor=HexColor("#176b9a"),spaceBefore=16,spaceAfter=8));styles.add(ParagraphStyle(name="H3x",parent=styles["Heading3"],fontSize=11,leading=14,textColor=HexColor("#243a46"),spaceBefore=10,spaceAfter=4));styles.add(ParagraphStyle(name="Bodyx",parent=styles["BodyText"],fontSize=9.5,leading=13,spaceAfter=6));styles.add(ParagraphStyle(name="Metax",parent=styles["BodyText"],fontSize=8.5,leading=11,textColor=HexColor("#516a77"),spaceAfter=5))
    def ascii_text(value):return value.replace("’","'").replace("‘","'").replace("“",'"').replace("”",'"').replace("–","-").replace("—","-").replace("…","...")
    story=[];raw_lines=text.splitlines();index=0
    while index<len(raw_lines):
        line=ascii_text(raw_lines[index].strip());index+=1
        if not line:story.append(Spacer(1,4));continue
        if line.startswith("# "):story.append(Paragraph(escape(line[2:]),styles["Title2"]));continue
        if line.startswith("## "):story.append(Paragraph(escape(line[3:]),styles["H2x"]));continue
        if line.startswith("### "):
            block=[Paragraph(escape(line[4:]),styles["H3x"])];
            while index<len(raw_lines) and not raw_lines[index].strip():index+=1
            while index<len(raw_lines) and not raw_lines[index].startswith("#"):
                value=ascii_text(raw_lines[index].strip());index+=1
                if value:
                    value=re.sub(r"\*\*(.*?)\*\*",r"<b>\1</b>",escape(value));block.append(Paragraph(value,styles["Bodyx"]))
                while index<len(raw_lines) and not raw_lines[index].strip():index+=1
            story.append(KeepTogether(block));continue
        if line.startswith("- ["):
            clean=re.sub(r"\[([^]]+)\]\([^)]+\)",r"\1",line[2:]);story.append(Paragraph("• "+escape(clean),styles["Metax"]));continue
        if line.startswith(">"):story.append(Paragraph(escape(line[1:].strip()),styles["Metax"]));continue
        line=re.sub(r"\*\*(.*?)\*\*",r"<b>\1</b>",escape(line));story.append(Paragraph(line,styles["Bodyx"]))
    def footer(canvas,doc):canvas.saveState();canvas.setFont("Helvetica",8);canvas.setFillColor(HexColor("#607985"));canvas.drawString(.65*inch,.4*inch,"Renegade Draft Room - 2026 Fantasy Research Brief");canvas.drawRightString(7.85*inch,.4*inch,f"Page {doc.page}");canvas.restoreState()
    SimpleDocTemplate(str(REPORT_PDF),pagesize=letter,rightMargin=.65*inch,leftMargin=.65*inch,topMargin=.65*inch,bottomMargin=.6*inch,title="2026 Fantasy Football Research Brief").build(story,onFirstPage=footer,onLaterPages=footer)

def main():
    load_env();grouped,sources=evidence();OUT.mkdir(parents=True,exist_ok=True);model=os.environ.get("FANTASY_RESEARCH_MODEL") or os.environ.get("ASSISTANT_GM_MODEL") or "gpt-5-mini"
    profiles,targets,team_targets,handcuffs,fantasypros,format_notes,auction=contextual_evidence()
    records=[input_record(player_id,rows,profiles,targets,team_targets,handcuffs,fantasypros,format_notes,auction) for player_id,rows in sorted(grouped.items(),key=lambda item:item[1][0]["player_name"])]
    cached={}
    pointer=ROOT/"data/processed/fantasy_research/latest.json"
    if pointer.exists():
        old=json.loads((ROOT/json.loads(pointer.read_text())["artifact"]).read_text());cached={r["player_id"]:r for r in old["summaries"]}
    changed=[r for r in records if cached.get(r["player_id"],{}).get("input_hash")!=r["input_hash"] or cached.get(r["player_id"],{}).get("prompt_version")!=PROMPT_VERSION or not cached.get(r["player_id"],{}).get("full_writeup")];generated=synthesize(changed,model) if changed else {}
    now=datetime.now(timezone.utc).isoformat();summaries=[]
    for record in records:
        previous=cached.get(record["player_id"])
        generated_summary=generated.get(record["player_id"])
        card_summary=generated_summary and generated_summary["card_summary"] or (previous and (previous.get("card_summary") or previous.get("summary")))
        full_writeup=generated_summary and generated_summary["full_writeup"] or (previous and previous.get("full_writeup"))
        if not card_summary or not full_writeup:raise RuntimeError(f"No complete AI synthesis generated for {record['player_name']}")
        preserve_pros_cons=previous and previous.get("pros_cons_input_hash")==record["input_hash"]
        summaries.append({"player_id":record["player_id"],"player_name":record["player_name"],"card_summary":card_summary,"full_writeup":full_writeup,"pros_summary":previous.get("pros_summary") if preserve_pros_cons else None,"cons_summary":previous.get("cons_summary") if preserve_pros_cons else None,"pros_cons_input_hash":previous.get("pros_cons_input_hash") if preserve_pros_cons else None,"pros_cons_prompt_version":previous.get("pros_cons_prompt_version") if preserve_pros_cons else None,"pros_cons_model":previous.get("pros_cons_model") if preserve_pros_cons else None,"pros_cons_generated_at":previous.get("pros_cons_generated_at") if preserve_pros_cons else None,"source_ids":sorted({r["source_id"] for r in record["evidence"]}|set(record["context_source_ids"])),"input_hash":record["input_hash"],"prompt_version":PROMPT_VERSION,"model":model,"generated_at":now if record["player_id"] in generated else previous["generated_at"]})
    artifact={"metadata":{"schema_version":2,"build_id":BUILD_ID,"built_at":now,"summary_count":len(summaries),"prompt_version":PROMPT_VERSION,"model":model},"summaries":summaries};artifact_path=OUT/"player_summaries.json";artifact_path.write_text(json.dumps(artifact,indent=2)+"\n");pointer.parent.mkdir(parents=True,exist_ok=True);pointer.write_text(json.dumps({"schema_version":2,"artifact":str(artifact_path.relative_to(ROOT)),"research_wiki":"/research"},indent=2)+"\n")
    print(json.dumps({"sources":len(sources),"takeaways":sum(map(len,grouped.values())),"players":len(summaries),"regenerated":len(changed),"research_wiki":"/research"}))

if __name__=="__main__":main()
