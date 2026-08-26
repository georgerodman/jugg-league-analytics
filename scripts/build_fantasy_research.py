#!/usr/bin/env python3
"""Build cached AI player syntheses and the offline fantasy research brief."""

import hashlib,json,os,re,time,urllib.request
from collections import defaultdict
from datetime import datetime,timezone
from html import escape
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROMPT_VERSION="fantasy-player-synthesis-v1"
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
    return "Target" if positive>negative else "Avoid" if negative>positive else "Watch"

def input_record(player_id,rows):
    compact=[{"source_id":r["source_id"],"publication":r["publication"],"author":r.get("author"),"date":r["published_at"],"label":r["label"],"sentiment":r["sentiment"],"summary":r["summary"],"rationale":r["rationale"],"risks":r["risks"],"formats":r.get("formats",[]),"price_condition":r.get("price_condition"),"assumptions":r.get("assumptions",[])} for r in rows]
    canonical=json.dumps(compact,sort_keys=True,separators=(",",":"));return {"player_id":player_id,"player_name":rows[0]["player_name"],"evidence":compact,"input_hash":hashlib.sha256(canonical.encode()).hexdigest()}

def response_text(payload):
    if isinstance(payload.get("output_text"),str):return payload["output_text"]
    return "".join(item.get("text","") for output in payload.get("output",[]) for item in output.get("content",[]) if item.get("type") in ("output_text","text"))

def synthesize(records,model):
    key=os.environ.get("OPENAI_API_KEY");
    if not key:raise RuntimeError("OPENAI_API_KEY is required to generate AI research summaries")
    results={}
    schema={"type":"object","properties":{"summaries":{"type":"array","items":{"type":"object","properties":{"player_id":{"type":"string"},"summary":{"type":"string"}},"required":["player_id","summary"],"additionalProperties":False}}},"required":["summaries"],"additionalProperties":False}
    for start in range(0,len(records),10):
        batch=records[start:start+10]
        instructions="You synthesize supplied fantasy-football research only. For each player, write one or two concise sentences that aggregate all evidence, state the overall view and main rationale, and include meaningful disagreement, risk, assumption, format, or price dependency. Do not add outside facts. Do not mention data structures or claim consensus when only one independent analyst is present."
        request={"model":model,"instructions":instructions,"input":json.dumps([{"player_id":r["player_id"],"player_name":r["player_name"],"evidence":r["evidence"]} for r in batch]),"max_output_tokens":2200,"store":False,"text":{"verbosity":"low","format":{"type":"json_schema","name":"player_summaries","strict":True,"schema":schema}}}
        req=urllib.request.Request("https://api.openai.com/v1/responses",data=json.dumps(request).encode(),headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(req,timeout=120) as response:parsed=json.loads(response.read())
        decoded=json.loads(response_text(parsed));results.update({row["player_id"]:row["summary"].strip() for row in decoded["summaries"]});print(f"AI summaries: {min(start+10,len(records))}/{len(records)}",flush=True);time.sleep(.15)
    return results

def markdown(grouped,summaries,sources):
    rows=[]
    for player_id,evidence_rows in grouped.items():
        positive,negative,count=opinion_counts(evidence_rows);tags=sorted({r["label"].title() for r in evidence_rows if r["label"] in ("sleeper","breakout","value","bust")})
        rows.append({"id":player_id,"name":evidence_rows[0]["player_name"],"action":action(evidence_rows),"positive":positive,"negative":negative,"count":count,"tags":tags,"summary":summaries[player_id]["summary"],"sources":sorted({r["source_id"] for r in evidence_rows}),"price":next((r.get("price_condition") for r in evidence_rows if r.get("price_condition")),None)})
    targets=sorted((r for r in rows if r["action"]=="Target"),key=lambda r:(-r["count"],-r["positive"],r["name"]));avoids=sorted((r for r in rows if r["action"]=="Avoid"),key=lambda r:(-r["count"],-r["negative"],r["name"]));divisive=sorted((r for r in rows if r["positive"] and r["negative"]),key=lambda r:(-r["count"],r["name"]));
    def section(title,items,limit=18):
        lines=[f"## {title}",""]
        for row in items[:limit]:
            meta=f"{row['positive']} positive, {row['negative']} negative; {row['count']} independent analyst{'s' if row['count']!=1 else ''}";tag=f" Tags: {', '.join(row['tags'])}." if row["tags"] else "";price=f" Price context: {row['price']}." if row["price"] else ""
            lines += [f"### {row['name']}","",f"**{row['action']} - {meta}.**{tag}{price}","",row["summary"],""]
        return lines
    lines=["# 2026 Fantasy Football Research Brief","",f"Generated {datetime.now().strftime('%B %d, %Y')} from {len(sources)} retained articles and {sum(len(v) for v in grouped.values())} structured player takeaways.","","> League lens: 10-team, non-PPR auction. Source articles using PPR, dynasty, deep-league, or superflex assumptions are identified in the underlying evidence and treated cautiously.","","## Executive summary","",f"The library currently covers {len(rows)} players. It produces {len(targets)} Target leans, {len(avoids)} Avoid leans, and {len(rows)-len(targets)-len(avoids)} balanced Watch cases before manual overrides.","","The strongest conclusions are the players supported or opposed by several independent analysts. A one-source recommendation is useful evidence, but it is not described as broad consensus.",""]
    lines+=section("Strongest targets",targets)
    lines+=section("Players to avoid at current price",avoids)
    lines+=section("Most divisive players",divisive,20)
    for tag,title in [("Sleeper","Sleepers and late-round targets"),("Value","Best values"),("Breakout","Breakout candidates"),("Bust","Bust concerns")]:lines+=section(title,sorted((r for r in rows if tag in r["tags"]),key=lambda r:(-r["count"],r["name"])),15)
    lines += ["## Source guide",""]
    for source in sorted(sources.values(),key=lambda s:(s["source_key"],s["published_at"],s["title"])):lines.append(f"- [{source['title']}]({source['url']}) - {source.get('author') or 'Staff'}, {source['published_at']} ({source['source_key']})")
    lines += ["","## Methodology", "", "Player votes are deduplicated by analyst, using the newest retained opinion for the deterministic positive/negative split. Target, Avoid, and Watch are normalized action signals; Sleeper, Breakout, Value, and Bust are descriptive tags. AI summaries are generated only from retained takeaways and cached by an input hash. Team-level articles provide context but do not create player votes. Manual overrides in the application affect the displayed flag only.",""]
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
            for _ in range(2):
                if index>=len(raw_lines) or raw_lines[index].startswith("#"):break
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
    records=[input_record(player_id,rows) for player_id,rows in sorted(grouped.items(),key=lambda item:item[1][0]["player_name"])]
    cached={}
    pointer=ROOT/"data/processed/fantasy_research/latest.json"
    if pointer.exists():
        old=json.loads((ROOT/json.loads(pointer.read_text())["artifact"]).read_text());cached={r["player_id"]:r for r in old["summaries"]}
    changed=[r for r in records if cached.get(r["player_id"],{}).get("input_hash")!=r["input_hash"]];generated=synthesize(changed,model) if changed else {}
    now=datetime.now(timezone.utc).isoformat();summaries=[]
    for record in records:
        previous=cached.get(record["player_id"])
        summary=generated.get(record["player_id"]) or (previous and previous["summary"])
        if not summary:raise RuntimeError(f"No AI summary generated for {record['player_name']}")
        summaries.append({"player_id":record["player_id"],"player_name":record["player_name"],"summary":summary,"source_ids":sorted({r["source_id"] for r in record["evidence"]}),"input_hash":record["input_hash"],"prompt_version":PROMPT_VERSION,"model":model,"generated_at":now if record["player_id"] in generated else previous["generated_at"]})
    artifact={"metadata":{"schema_version":1,"build_id":BUILD_ID,"built_at":now,"summary_count":len(summaries),"prompt_version":PROMPT_VERSION,"model":model},"summaries":summaries};artifact_path=OUT/"player_summaries.json";artifact_path.write_text(json.dumps(artifact,indent=2)+"\n");pointer.parent.mkdir(parents=True,exist_ok=True);pointer.write_text(json.dumps({"schema_version":1,"artifact":str(artifact_path.relative_to(ROOT)),"research_brief_markdown":str(REPORT_MD.relative_to(ROOT)),"research_brief_pdf":str(REPORT_PDF.relative_to(ROOT))},indent=2)+"\n")
    summary_map={row["player_id"]:row for row in summaries};md=markdown(grouped,summary_map,sources);REPORT_MD.parent.mkdir(parents=True,exist_ok=True);REPORT_MD.write_text(md);pdf_from_markdown(md);print(json.dumps({"sources":len(sources),"takeaways":sum(map(len,grouped.values())),"players":len(summaries),"regenerated":len(changed),"markdown":str(REPORT_MD),"pdf":str(REPORT_PDF)}))

if __name__=="__main__":main()
