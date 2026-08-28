import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { z } from "zod";
import { DraftService } from "./DraftService";

const summarySchema=z.object({player_id:z.string().min(1),card_summary:z.string().min(1),full_writeup:z.string().min(1),pros_summary:z.string().min(1).nullable().optional(),cons_summary:z.string().min(1).nullable().optional(),source_ids:z.array(z.string().min(1)).min(1),input_hash:z.string().min(1),prompt_version:z.string().min(1),model:z.string().min(1),generated_at:z.string().min(1)});
const artifactSchema=z.object({metadata:z.object({schema_version:z.number().int().positive(),build_id:z.string().min(1),summary_count:z.number().int().nonnegative()}),summaries:z.array(summarySchema)});
const pointerSchema=z.object({artifact:z.string().min(1)});

export function importFantasyResearchSynthesis(service:DraftService,root:string):void{
  let pointer:unknown;
  try{pointer=JSON.parse(readFileSync(resolve(root,"data/processed/fantasy_research/latest.json"),"utf8"));}catch{return;}
  const {artifact}=pointerSchema.parse(pointer),parsed=artifactSchema.parse(JSON.parse(readFileSync(resolve(root,artifact),"utf8")));
  if(parsed.metadata.summary_count!==parsed.summaries.length)throw new Error("Fantasy-research summary count mismatch");
  const insert=service.db.prepare("INSERT INTO fantasy_player_summaries(player_id,summary,full_writeup,pros_summary,cons_summary,source_ids_json,input_hash,prompt_version,model,generated_at) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(player_id) DO UPDATE SET summary=excluded.summary,full_writeup=excluded.full_writeup,pros_summary=excluded.pros_summary,cons_summary=excluded.cons_summary,source_ids_json=excluded.source_ids_json,input_hash=excluded.input_hash,prompt_version=excluded.prompt_version,model=excluded.model,generated_at=excluded.generated_at");
  service.db.transaction(()=>{for(const row of parsed.summaries){if(service.db.prepare("SELECT 1 FROM players WHERE id=?").get(row.player_id))insert.run(row.player_id,row.card_summary,row.full_writeup,row.pros_summary??null,row.cons_summary??null,JSON.stringify(row.source_ids),row.input_hash,row.prompt_version,row.model,row.generated_at);}})();
}
