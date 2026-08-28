"use client";

import { useState } from "react";
import styles from "./research.module.css";

type Action="target"|"avoid"|null;
type ActionOverride="target"|"avoid"|"off"|null;
type Tag="sleeper"|"breakout"|"value"|"bust";
type Props={playerId:string;derivedAction:Action;override:ActionOverride;tags:string[];derivedTags:string[];tagOverrides:Partial<Record<Tag,boolean>>};
const actions=["target","avoid"] as const;
const tagOptions:Tag[]=["sleeper","breakout","value","bust"];

export function ResearchControls({playerId,derivedAction,override:initialOverride,tags:initialTags,derivedTags,tagOverrides:initialTagOverrides}:Props){
  const [override,setOverride]=useState<ActionOverride>(initialOverride),[tags,setTags]=useState(new Set(initialTags)),[tagOverrides,setTagOverrides]=useState(initialTagOverrides),[saving,setSaving]=useState(false),[error,setError]=useState("");
  const displayedAction=override==="off"?null:override??derivedAction;
  async function post(action:unknown){setSaving(true);setError("");try{const response=await fetch("/api/draft",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(action)});if(!response.ok)throw new Error("Could not save override");}catch(reason){setError(reason instanceof Error?reason.message:"Could not save override");throw reason;}finally{setSaving(false);}}
  async function setAction(value:typeof actions[number]){const previous=override;let next:ActionOverride=value,requestOverride:"auto"|"target"|"avoid"|"off"=value;if(displayedAction===value){next="off";requestOverride="off";}else if(value===derivedAction){next=null;requestOverride="auto";}setOverride(next);try{await post({type:"fantasyAnalysisOverride",playerId,override:requestOverride});}catch{setOverride(previous);}}
  async function toggleTag(tag:Tag){const previousTags=new Set(tags),previousOverrides={...tagOverrides},selected=tags.has(tag),suggested=derivedTags.includes(tag);let requestOverride:"auto"|"on"|"off",nextSelected:boolean;if(selected){requestOverride=suggested?"off":"auto";nextSelected=false;}else{requestOverride=suggested?"auto":"on";nextSelected=true;}const nextTags=new Set(tags);nextSelected?nextTags.add(tag):nextTags.delete(tag);setTags(nextTags);setTagOverrides(current=>{const next={...current};if(requestOverride==="auto")delete next[tag];else next[tag]=requestOverride==="on";return next;});try{await post({type:"fantasyAnalysisTagOverride",playerId,tag,override:requestOverride});}catch{setTags(previousTags);setTagOverrides(previousOverrides);}}
  return <div className={styles.classificationEditor} style={{minWidth:0,maxWidth:"100%",flexShrink:1}}>
    {(saving||error)&&<div aria-live="polite" style={{width:100,textAlign:"right",color:error?"#a33d34":"#71838d",fontSize:10,fontWeight:750}}>{error||"Saving…"}</div>}
    <div className={styles.actionEditor}>{actions.map(value=>{const selected=displayedAction===value,suggested=value===derivedAction,tone=value==="target"?{borderColor:selected?"#23794b":"#8bb89a",background:selected?"#23794b":"#fff",color:selected?"#fff":"#176039",fontWeight:700}:{borderColor:selected?"#a83c32":"#d4a19a",background:selected?"#a83c32":"#fff",color:selected?"#fff":"#96352c",fontWeight:700};return <button key={value} disabled={saving} aria-pressed={selected} title={selected?"Selected — click again to turn this flag off":suggested?"Research recommendation — click to restore it":"Click to select this action"} style={tone} className={`${selected?styles.selectedOverride:""} ${selected&&override!==null?styles.manualAction:""}`} onClick={()=>void setAction(value)}>{value[0]!.toUpperCase()+value.slice(1)}{suggested&&<span aria-hidden="true" style={{position:"absolute",top:4,right:4,width:4,height:4,borderRadius:"50%",background:selected?"#fff":"#277ca6",boxShadow:selected?"0 0 0 1px #277ca6":"0 0 0 1px #fff"}}/>}</button>;})}</div>
    <span aria-hidden="true" style={{alignSelf:"stretch",minHeight:28,borderLeft:"1px solid #c7d3d9"}}/>
    <div className={styles.tagEditor}>{tagOptions.map(tag=>{const selected=tags.has(tag),suggested=derivedTags.includes(tag),tone=selected?{borderColor:"#1d6f98",background:"#277ca6",color:"#fff",fontWeight:700}:{fontWeight:700};return <button key={tag} disabled={saving} aria-pressed={selected} title={selected?"Selected — click again to remove this tag":suggested?"Research suggestion — click to restore it":"Click to add this tag"} style={tone} className={`${selected?styles.selectedTag:""} ${tag in tagOverrides?styles.manualTag:""}`} onClick={()=>void toggleTag(tag)}>{tag[0]!.toUpperCase()+tag.slice(1)}{suggested&&<span aria-hidden="true" style={{position:"absolute",top:4,right:4,width:4,height:4,borderRadius:"50%",background:selected?"#fff":"#277ca6",boxShadow:selected?"0 0 0 1px #277ca6":"0 0 0 1px #fff"}}/>}</button>;})}</div>
  </div>;
}
