import { assistantResponseSchema, ASSISTANT_PROMPT_VERSION, type AssistantContext, type AssistantResponse } from "./contracts";

function values(context:AssistantContext){const numbers=new Set<number>(),players=new Set<string>();const walk=(value:unknown)=>{if(typeof value==="number")numbers.add(value);else if(value&&typeof value==="object")for(const [key,item] of Object.entries(value)){if(key==="name"&&typeof item==="string")players.add(item);walk(item);}};walk(context);return{numbers,players};}
export function validateGroundedResponse(context:AssistantContext,text:string,referencedPacketFields:string[]):AssistantResponse{
  const issues:string[]=[],known=values(context);
  for(const match of text.matchAll(/\$(\d+)/g))if(!known.numbers.has(Number(match[1])))issues.push(`Unrecognized dollar amount $${match[1]}`);
  if(/\b\d+(?:\.\d+)?%\s+(?:chance|probability)\s+(?:to|of)\s+win(?:ning)?\b|\btitle probability\s+(?:is|of)\s+\d/i.test(text))issues.push("Shadow signal overstated as title probability");
  if(/(?:nominate|nomination choice is)\s+([A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+)+)/.test(text)){const candidate=text.match(/(?:nominate|nomination choice is)\s+([A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+)+)/)?.[1];if(candidate&&!context.upcomingTargets.some(t=>t.player.name===candidate))issues.push("Nomination suggestion is outside Upcoming Targets");}
  if(!referencedPacketFields.length)issues.push("No packet fields referenced");
  return assistantResponseSchema.parse({text,referencedPacketFields,stateVersion:context.stateVersion,promptVersion:ASSISTANT_PROMPT_VERSION,uncertaintyFlags:context.missingOrStale,grounding:{valid:issues.length===0,issues}});
}
