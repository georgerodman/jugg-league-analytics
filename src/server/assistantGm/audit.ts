import { appendFile } from "node:fs/promises";
import { mkdir } from "node:fs/promises";
import { dirname,join } from "node:path";
export type AuditRecord={interactionId:string;startedAt:string;completedAt:string;draftStateVersion:number;trigger:string;contextSchemaVersion:string;contextHash:string;provider:string;promptVersion:string;userQuestion:string|null;status:"completed"|"failed"|"timed_out"|"cancelled"|"stale";responseText?:string;safeErrorCategory?:string;grounding:{valid:boolean;issues:string[]}|null};
export async function appendAssistantAudit(record:AuditRecord){try{const path=process.env.ASSISTANT_GM_AUDIT_PATH??join(process.cwd(),".local","assistant-gm-audit.jsonl");await mkdir(dirname(path),{recursive:true});await appendFile(path,`${JSON.stringify(record)}\n`,{encoding:"utf8",mode:0o600});}catch{/* Audit failure must never block draft operation. */}}
