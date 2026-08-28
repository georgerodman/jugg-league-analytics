import Link from "next/link";
import type { Metadata } from "next";
import { readDraftRoom } from "../../src/server/draftStore";
import { ResearchControls } from "./ResearchControls";
import { ResearchWriteup } from "../../src/ui/research/ResearchWriteup";
import styles from "./research.module.css";

export const dynamic="force-dynamic";
export const metadata:Metadata={title:"Renegade Research"};

type ResearchSource={url:string;sourceTitle:string;sentiment:"positive"|"negative"|"neutral";summary:string;rationale:string;risks:string[]};
type PlayerInjury={status:string|null;statusShort:string|null;injuryType:string|null;comment:string|null;updatedAt:string|null;probabilityOfPlaying:string|null;practiceReportInjuryType:string|null;practice:string[];irWeeks:number[]};
type PlayerNews={id:string;title:string;description:string|null;impact:string|null;author:string|null;createdAt:string|null;url:string|null};
type ResearchPlayer={id:string;name:string;position:string;nflTeam:string|null;byeWeek:number|null;birthDate:string|null;positionRank:number|null;expectedPrice:number|null;priceLow:number|null;priceHigh:number|null;liveExpectedPrice:number|null;livePriceLow:number|null;livePriceHigh:number|null;injury:PlayerInjury|null;recentNews:PlayerNews[];fantasyAnalysis:ResearchSource[];analystConsensus:{derivedAction:"target"|"avoid"|null;override:"target"|"avoid"|"off"|null;tags:string[];derivedTags:string[];tagOverrides:Partial<Record<"sleeper"|"breakout"|"value"|"bust",boolean>>;positiveCount:number;negativeCount:number;independentOpinionCount:number;pros:string[];cons:string[];commonCase:string|null;mainConcern:string|null;aiSummary:{fullWriteup:string|null;prosSummary:string|null;consSummary:string|null}|null}};

function anchor(player:ResearchPlayer){return `player-${player.id.replaceAll(":","-")}`;}
function actionLabel(player:ResearchPlayer){const {derivedAction,override}=player.analystConsensus,action=override==="off"?null:override??derivedAction;return action?`${action[0]!.toUpperCase()}${action.slice(1)}`:override==="off"?"Hidden":"Unclassified";}
function xPrice(player:ResearchPlayer){const price=player.liveExpectedPrice??player.expectedPrice;return price==null?"—":`$${Math.round(price)}`;}
function priceRange(player:ResearchPlayer){const low=player.livePriceLow??player.priceLow,high=player.livePriceHigh??player.priceHigh;return low==null||high==null?null:`$${Math.round(low)}–$${Math.round(high)}`;}
function playerAge(birthDate:string|null){if(!birthDate)return null;const born=new Date(`${birthDate}T00:00:00Z`),today=new Date();let age=today.getUTCFullYear()-born.getUTCFullYear();if(today.getUTCMonth()<born.getUTCMonth()||(today.getUTCMonth()===born.getUTCMonth()&&today.getUTCDate()<born.getUTCDate()))age--;return age;}
function contextDate(value:string|null){if(!value)return null;const parsed=new Date(`${value.replace(" ","T")}${value.includes("Z")||value.includes("+")?"":"Z"}`);return Number.isNaN(parsed.valueOf())?value:parsed.toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric"});}
function injurySummary(injury:PlayerInjury){const probability=injury.probabilityOfPlaying==null?null:Number(injury.probabilityOfPlaying),probabilityLabel=probability==null||Number.isNaN(probability)?null:`${Math.round((probability<=1?probability*100:probability)*10)/10}% probability of playing`;return [injury.status,injury.injuryType??injury.practiceReportInjuryType,injury.comment,probabilityLabel,injury.practice.length?`Practice: ${injury.practice.join(" / ")}`:null,injury.irWeeks.length?`IR weeks: ${injury.irWeeks.join(", ")}`:null].filter(Boolean).join(" · ");}

export default function ResearchWikiPage(){
  const data=readDraftRoom();
  const players=(data.players as ResearchPlayer[]).filter(player=>player.analystConsensus.aiSummary?.fullWriteup).sort((a,b)=>a.name.localeCompare(b.name));
  const groups=["QB","RB","WR","TE","K","DEF"].map(position=>({position,players:players.filter(player=>player.position===position).sort((a,b)=>(a.positionRank??Number.MAX_SAFE_INTEGER)-(b.positionRank??Number.MAX_SAFE_INTEGER)||a.name.localeCompare(b.name))})).filter(group=>group.players.length);
  const generatedAt=data.researchStatus.lastSummaryGeneratedAt?new Date(data.researchStatus.lastSummaryGeneratedAt).toLocaleString("en-US",{dateStyle:"long",timeStyle:"short"}):"Unknown";
  return <main className={styles.wiki}>
    <header className={styles.header}>
      <div><small>RENEGADE DRAFT ROOM</small><h1>Fantasy Research Wiki</h1><p>{players.length} full player writeups · Updated {generatedAt} · Available offline</p></div>
      <Link href="/board">← Draft board</Link>
    </header>
    <nav className={styles.jumpNav} aria-label="Research sections"><a href="#index">Player index</a>{groups.map(group=><a key={group.position} href={`#position-${group.position.toLowerCase()}`}>{group.position} <span>{group.players.length}</span></a>)}</nav>
    <section className={styles.intro}><strong>How to use this wiki</strong><p>Use your browser’s Find command to search for any player, analyst, risk, or theme. Target and Avoid identify actionable research direction; no selected action means neutral or unresolved. Sleeper, Breakout, Value, and Bust describe the argument. Full writeups preserve price, role, injury, and format caveats from the retained research.</p></section>
    <section className={styles.index} id="index"><h2>Player index</h2><div>{players.map(player=><a href={`#${anchor(player)}`} key={player.id}><span>{player.name}</span><small>{player.position} · {actionLabel(player)}</small></a>)}</div></section>
    {groups.map(group=><section className={styles.positionSection} id={`position-${group.position.toLowerCase()}`} key={group.position}>
      <div className={styles.sectionHeading}><h2>{group.position} full writeups</h2><a href="#index">Back to index ↑</a></div>
      {group.players.map(player=>{const consensus=player.analystConsensus,summary=consensus.aiSummary!,range=priceRange(player),pros=summary.prosSummary??consensus.commonCase??"No clear upside case is captured in the current research.",cons=summary.consSummary??consensus.mainConcern??"No specific downside case is captured in the current research.";const sources=[...new Map(player.fantasyAnalysis.map(source=>[source.url,source])).values()];return <ResearchWriteup key={player.id} id={anchor(player)} name={player.name} positionPrice={`${player.position}${player.positionRank??"—"} - ${xPrice(player)}${range?` (${range})`:""}`} playerMeta={`${player.nflTeam??"Free agent"}${player.byeWeek?` · Bye ${player.byeWeek}`:""}${playerAge(player.birthDate)!=null?` · Age ${playerAge(player.birthDate)}`:""}`} controls={<ResearchControls playerId={player.id} derivedAction={consensus.derivedAction} override={consensus.override} tags={consensus.tags} derivedTags={consensus.derivedTags} tagOverrides={consensus.tagOverrides}/>} positiveCount={consensus.positiveCount} negativeCount={consensus.negativeCount} independentOpinionCount={consensus.independentOpinionCount} pros={pros} cons={cons} fullWriteup={summary.fullWriteup!} context={player.injury?<div className={`${styles.contextCallout} ${styles.injuryCallout}`}><strong>Injury:</strong> <span>{injurySummary(player.injury)}</span>{contextDate(player.injury.updatedAt)&&<small>FantasyPros · Updated {contextDate(player.injury.updatedAt)}</small>}</div>:null} sources={sources.map(source=>({url:source.url,title:source.sourceTitle}))} indexHref="#index"/>;})}
    </section>)}
  </main>;
}
