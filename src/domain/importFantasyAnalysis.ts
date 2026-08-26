import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { z } from "zod";
import { DraftService } from "./DraftService";

const takeawaySchema=z.object({player_id:z.string().min(1),player_name:z.string().min(1),label:z.enum(["sleeper","target","avoid","bust","value","breakout"]),sentiment:z.enum(["positive","mixed","negative"]),summary:z.string().min(1),rationale:z.string().min(1),risks:z.array(z.string().min(1))});
const artifactSchema=z.object({metadata:z.object({schema_version:z.number().int().positive(),build_id:z.string().min(1),built_at:z.string().min(1),season:z.number().int(),takeaway_count:z.number().int().nonnegative()}),source:z.object({id:z.string().min(1),source_key:z.string().min(1),title:z.string().min(1),author:z.string().nullable(),url:z.string().url(),published_at:z.string().min(1),season:z.number().int(),content_type:z.string().min(1),summary:z.string().min(1).optional()}),takeaways:z.array(takeawaySchema)});
const pointerSchema=z.object({schema_version:z.number().int().positive(),artifacts:z.array(z.string().min(1))});

export function importFantasyAnalysis(service:DraftService,root:string):void{
  let pointer:unknown;
  try{pointer=JSON.parse(readFileSync(resolve(root,"data/processed/fantasy_analysis/latest.json"),"utf8"));}catch{return;}
  const parsedPointer=pointerSchema.parse(pointer);
  service.db.transaction(()=>{
    for(const relativePath of parsedPointer.artifacts){
      const raw=readFileSync(resolve(root,relativePath),"utf8"),artifact=artifactSchema.parse(JSON.parse(raw));
      if(artifact.metadata.takeaway_count!==artifact.takeaways.length)throw new Error(`Fantasy-analysis count mismatch in ${relativePath}`);
      const artifactId=`artifact:fantasy-analysis:${artifact.metadata.build_id}:${artifact.source.id}`;
      service.db.prepare("INSERT OR IGNORE INTO artifact_imports(id,artifact_type,schema_version,build_id,relative_path,sha256,metadata_json) VALUES(?,?,?,?,?,?,?)").run(artifactId,"fantasy_analysis",artifact.metadata.schema_version,artifact.metadata.build_id,relativePath,createHash("sha256").update(raw).digest("hex"),JSON.stringify(artifact.metadata));
      service.db.prepare("INSERT INTO fantasy_analysis_sources(id,artifact_id,source_key,title,author,url,published_at,season,content_type,source_summary) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET artifact_id=excluded.artifact_id,source_key=excluded.source_key,title=excluded.title,author=excluded.author,url=excluded.url,published_at=excluded.published_at,season=excluded.season,content_type=excluded.content_type,source_summary=excluded.source_summary,imported_at=CURRENT_TIMESTAMP").run(artifact.source.id,artifactId,artifact.source.source_key,artifact.source.title,artifact.source.author,artifact.source.url,artifact.source.published_at,artifact.source.season,artifact.source.content_type,artifact.source.summary??null);
      const insert=service.db.prepare("INSERT INTO fantasy_player_takeaways(source_id,player_id,label,sentiment,summary,rationale,risks_json) VALUES(?,?,?,?,?,?,?) ON CONFLICT(source_id,player_id,label) DO UPDATE SET sentiment=excluded.sentiment,summary=excluded.summary,rationale=excluded.rationale,risks_json=excluded.risks_json");
      for(const takeaway of artifact.takeaways){
        if(!service.db.prepare("SELECT 1 FROM players WHERE id=?").get(takeaway.player_id))throw new Error(`Fantasy-analysis player is not in the registry: ${takeaway.player_id}`);
        insert.run(artifact.source.id,takeaway.player_id,takeaway.label,takeaway.sentiment,takeaway.summary,takeaway.rationale,JSON.stringify(takeaway.risks));
      }
    }
  })();
}
