import { createHash,randomUUID } from "node:crypto";
import { readDraftRoom } from "../draftStore";
import { appendAssistantAudit, type AuditRecord } from "./audit";
import { buildAssistantContext } from "./context";
import { conversationTurnSchema, type AssistantContext } from "./contracts";
import type { z } from "zod";
import { validateGroundedResponse } from "./grounding";
import { buildAssistantPrompt } from "./prompt";
import { configuredProvider, type AssistantProvider } from "./provider";

export type AssistantEvent={type:"meta"|"delta"|"complete"|"error";interactionId:string;stateVersion:number;text?:string;response?:unknown;code?:string};
export async function* streamAssistant(input:{trigger:AssistantContext["trigger"];question?:string|null;focusPlayerId?:string|null;conversationHistory?:z.infer<typeof conversationTurnSchema>[]},options:{provider?:AssistantProvider;timeoutMs?:number;signal?:AbortSignal}={}):AsyncGenerator<AssistantEvent>{
  const interactionId=randomUUID(),startedAt=new Date().toISOString(),view=readDraftRoom(),context=buildAssistantContext(view,input),serialized=JSON.stringify(context),contextHash=createHash("sha256").update(serialized).digest("hex"),provider=options.provider??configuredProvider(),controller=new AbortController(),timeoutMs=options.timeoutMs??Number(process.env.ASSISTANT_GM_TIMEOUT_MS??12000),cancel=()=>controller.abort("cancelled"),timer=setTimeout(()=>controller.abort("timeout"),timeoutMs);options.signal?.addEventListener("abort",cancel,{once:true});let text="",status:AuditRecord["status"]="failed",grounding:AuditRecord["grounding"]=null,safeErrorCategory:string|undefined;
  yield {type:"meta",interactionId,stateVersion:context.stateVersion};
  try{for await(const delta of provider.stream({prompt:buildAssistantPrompt(context),context,signal:controller.signal,maxOutputCharacters:5000})){text+=delta;yield{type:"delta",interactionId,stateVersion:context.stateVersion,text:delta};}
    const currentVersion=readDraftRoom().draft.stateVersion;if(currentVersion!==context.stateVersion){status="stale";safeErrorCategory="STATE_ADVANCED";yield{type:"error",interactionId,stateVersion:context.stateVersion,code:"STALE"};return;}
    const response=validateGroundedResponse(context,text,["focus.recommendation","focus.walkAway","alternatives","renegades","whatChanged"]);grounding=response.grounding;if(!response.grounding.valid){safeErrorCategory="GROUNDING_FAILED";yield{type:"error",interactionId,stateVersion:context.stateVersion,code:"UNGROUNDED"};return;}status="completed";yield{type:"complete",interactionId,stateVersion:context.stateVersion,response};
  }catch(error){status=controller.signal.aborted?(controller.signal.reason==="timeout"?"timed_out":"cancelled"):"failed";safeErrorCategory=status==="timed_out"?"TIMEOUT":status==="cancelled"?"CANCELLED":error instanceof Error&&error.message==="PROVIDER_UNAVAILABLE"?"UNAVAILABLE":"PROVIDER_FAILURE";yield{type:"error",interactionId,stateVersion:context.stateVersion,code:safeErrorCategory};}
  finally{clearTimeout(timer);options.signal?.removeEventListener("abort",cancel);await appendAssistantAudit({interactionId,startedAt,completedAt:new Date().toISOString(),draftStateVersion:context.stateVersion,trigger:context.trigger,contextSchemaVersion:context.schemaVersion,contextHash,provider:provider.id,promptVersion:buildAssistantPrompt(context).version,userQuestion:context.userQuestion,status,...(status==="completed"?{responseText:text}:safeErrorCategory?{safeErrorCategory}:{}),grounding});}
}
