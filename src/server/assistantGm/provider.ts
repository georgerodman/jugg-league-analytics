import type { AssistantContext } from "./contracts";
import type { ReturnTypeOfPrompt } from "./types";

export type ProviderRequest={prompt:ReturnTypeOfPrompt;context:AssistantContext;signal:AbortSignal;maxOutputCharacters:number};
export interface AssistantProvider{readonly id:string;stream(request:ProviderRequest):AsyncIterable<string>}

function mockText(context:AssistantContext){
  const next=context.upcomingTargets[0],radar=context.upcomingTargets.slice(0,3);
  if((context.trigger==="sale"||context.trigger==="correction")&&radar.length){const heading=context.nominationContext.isRenegadesTurn?"It’s your nomination turn. Consider these options":"Put these options on your radar";return `${heading}: ${radar.map((target,index)=>`${index+1}) ${target.player.name} (${target.player.position})—target $${target.targetPrice}, Walk-Away $${target.walkAway}; ${target.conditionalPlan}${target.fallback?` Fallback: ${target.fallback}.`:""}`).join(" ")}`;}
  const f=context.focus;if(!f)return next?`Keep ${next.player.name} on your radar; the current target is $${next.targetPrice}.`:"Select a player and I’ll help with the decision.";
  const ordered=[...(f.priceBands??[])].sort((a,b)=>a.from-b.from),active=ordered.find(row=>row.label.toLowerCase().replace(" ","_")===f.recommendation.band.replace("strong_pursue","great").replace("lean_pursue","good").replace("lean_pass","poor").replace("strong_pass","bad"))??ordered.find(row=>row.from>0),nextBand=active?ordered.find(row=>row.from>active.from):null;
  const action=f.recommendation.band==="strong_pursue"?"Strongly pursue":f.recommendation.band==="lean_pursue"?"Pursue with discipline":f.recommendation.band==="lean_pass"?"Pass for now":f.recommendation.band==="strong_pass"?"Avoid at this price":"Treat this as a close call";
  const through=active?.to??f.walkAway,alternatives=context.alternatives.slice(0,3).map(row=>row.player.name),needs=context.renegades?.needs.slice(0,3)??[];
  const boundary=through!=null?`${action} ${f.player.name} through $${through}.`:`I'd ${action.toLowerCase()} on ${f.player.name} at the expected price.`;
  const transition=nextBand?`At $${nextBand.from}, scale back because the cost starts changing the roster tradeoff.`:f.walkAway!=null?`Above $${f.walkAway}, stop and preserve flexibility.`:"";
  const why=alternatives.length?`Alternatives recorded by the engine are ${alternatives.join(", ")}.`:needs.length?`The remaining roster needs are ${needs.join(", ")}, and no close alternative is recorded.`:"No close alternative or roster-need evidence is recorded.";
  return `${boundary} ${transition} ${why}`.replace(/\s+/g," ").trim();
}
export class MockAssistantProvider implements AssistantProvider{
  readonly id="mock-grounded-v1";
  async *stream({context,signal,maxOutputCharacters}:ProviderRequest){const answer=mockText(context).slice(0,maxOutputCharacters);for(const part of answer.match(/.{1,24}(?:\s|$)/g)??[answer]){if(signal.aborted)throw new DOMException("Cancelled","AbortError");yield part;}}
}

export class OpenAiTextProvider implements AssistantProvider{
  readonly id=`openai:${process.env.ASSISTANT_GM_MODEL??"gpt-5-mini"}`;
  async *stream({prompt,signal,maxOutputCharacters}:ProviderRequest){
    const key=process.env.OPENAI_API_KEY;if(!key)throw new Error("PROVIDER_UNAVAILABLE");
    const response=await fetch("https://api.openai.com/v1/responses",{method:"POST",signal,headers:{authorization:`Bearer ${key}`,"content-type":"application/json"},body:JSON.stringify({model:process.env.ASSISTANT_GM_MODEL??"gpt-5-mini",instructions:prompt.system,input:prompt.user,stream:true,max_output_tokens:500,text:{verbosity:"low"},store:false,tools:[]})});
    if(!response.ok||!response.body)throw new Error("PROVIDER_FAILURE");
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer="",count=0;
    while(true){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const lines=buffer.split("\n");buffer=lines.pop()??"";for(const line of lines){if(!line.startsWith("data: ")||line==="data: [DONE]")continue;try{const event=JSON.parse(line.slice(6));if(event.type==="response.output_text.delta"&&typeof event.delta==="string"){const delta=event.delta.slice(0,Math.max(0,maxOutputCharacters-count));count+=delta.length;if(delta)yield delta;if(count>=maxOutputCharacters)return;}}catch{continue;}}}
  }
}
export function configuredProvider():AssistantProvider{return process.env.ASSISTANT_GM_PROVIDER==="openai"?new OpenAiTextProvider():new MockAssistantProvider();}
