import { existsSync, mkdirSync, readFileSync, renameSync, rmSync } from "node:fs";
import { join, resolve } from "node:path";
import { randomUUID } from "node:crypto";
import { createHash } from "node:crypto";
import { z } from "zod";
import { DraftService, DomainError } from "../domain/DraftService";
import { initializeFromArtifacts } from "../domain/importDraftArtifacts";
import { importFantasyAnalysis } from "../domain/importFantasyAnalysis";
import { importFantasyResearchSynthesis } from "../domain/importFantasyResearchSynthesis";
import { sheetSyncStatus } from "./googleSheetsSync";
import { draftRoadmap, liveLeaderboard, nominationDecision, type DecisionPlayer, type DecisionTeam, type Position } from "../domain/liveDecisionEngine";

const ROOT=process.cwd(), DRAFT_ID="jugg-2026", DATA_DIR=join(ROOT,".local");
const DATABASE_PATH=process.env.RENEGADE_DB_PATH??join(DATA_DIR,"renegade-draft-room.sqlite");

type OwnerProfile={owner:string;evidence_strength:string;construction_style:string;positions:Record<string,{signal:string;direction_consistency:number}>;repeat_players:{internal_player_id:string;player_name:string;times_drafted:number}[]};
type TeamPreference={team:string;position:"ALL"|"QB"|"RB"|"WR"|"TE"|"K"|"DEF";preference:"prefer"|"avoid";adjustment:number;note:string};
type Strategy={buildStyle:"balanced"|"stars_and_scrubs"|"value_first";riskTolerance:"conservative"|"balanced"|"aggressive";byeWeekMode:"ignore"|"soft"|"strict";maxSameBye:number;targetPremium:number;situations:string[];teamPreferences:TeamPreference[];notes:string};
type ProductionLabel="Elite"|"Premium"|"Starter"|"Depth"|"Replacement";
type SituationSignal={key:string;tone:"positive"|"negative"|"neutral";text:string;priority:number};
const DEFAULT_STRATEGY:Strategy={buildStyle:"balanced",riskTolerance:"balanced",byeWeekMode:"soft",maxSameBye:2,targetPremium:3,situations:[],teamPreferences:[],notes:""};
let decisionCache:{key:string;leaderboard:any[];championshipDecision:any;targets:any[];impacts:any[]}|null=null;
declare global { var __renegadeDraftService:DraftService|undefined; }

function latest(path:string):any{return JSON.parse(readFileSync(resolve(ROOT,path),"utf8"));}
function priorTeamByPlayer():Map<string,string>{
  try{
    const pointer=latest("data/processed/nflverse/latest.json"),snapshot=String(pointer.snapshot_id),rows=readFileSync(resolve(ROOT,`data/processed/nflverse/${snapshot}/player_stats_2025.csv`),"utf8").split(/\r?\n/),result=new Map<string,string>();
    for(const row of rows.slice(1)){const match=row.match(/^([^,]+),.*?,2025,\d+,([A-Z]{2,3}),/);if(match?.[1]&&match[2])result.set(`nfl:gsis:${match[1]}`,match[2]);}
    return result;
  }catch{return new Map();}
}
type TeamDepthChart={QB:string[];RB:string[];WR:string[];TE:string[]};
function teamDepthCharts():Map<string,TeamDepthChart>{
  try{
    const pointer=latest("data/processed/nflverse_depth_charts/2026/latest.json"),artifact=latest(pointer.artifact),result=new Map<string,TeamDepthChart>();
    for(const team of Array.isArray(artifact.teams)?artifact.teams:[]){
      const offense=team.fantasy_offense??{},names=(group:"QB"|"RB"|"WR"|"TE",limit:number)=>(Array.isArray(offense[group])?offense[group]:[]).filter((row:any)=>group!=="RB"||row.position_abbreviation!=="FB").map((row:any)=>row.name).filter(Boolean).slice(0,limit);
      result.set(team.team,{QB:names("QB",2),RB:names("RB",3),WR:names("WR",4),TE:names("TE",2)});
    }
    return result;
  }catch{return new Map();}
}
function fantasyProsContextByPlayer():Map<string,{injury:any|null;recentNews:any[]}>{
  try{
    const pointer=latest("data/processed/fantasypros_context/2026/latest.json"),artifact=latest(pointer.artifact);
    const result=new Map<string,{injury:any|null;recentNews:any[]}>();
    for(const context of Array.isArray(artifact.ai_player_context)?artifact.ai_player_context:[]){
      if(!context.internal_player_id)continue;
      const injury=context.injury?{status:context.injury.status,statusShort:context.injury.status_short,injuryType:context.injury.injury_type,comment:context.injury.comment,updatedAt:context.injury.injury_update_date,probabilityOfPlaying:context.injury.probability_of_playing,practiceReportInjuryType:context.injury.practice_report_injury_type,practice:[context.injury.practice_1,context.injury.practice_2,context.injury.practice_3].filter(Boolean),irWeeks:context.injury.ir_weeks??[]}:null;
      const recentNews=(Array.isArray(context.recent_news)?context.recent_news:[]).map((item:any)=>({id:String(item.news_id),title:item.title,description:item.description,impact:item.impact,author:item.author,createdAt:item.created_at,url:item.url}));
      result.set(context.internal_player_id,{injury,recentNews});
    }
    return result;
  }catch{return new Map();}
}
const TEAM_NAMES:Record<string,string>={ARI:"Arizona Cardinals",ATL:"Atlanta Falcons",BAL:"Baltimore Ravens",BUF:"Buffalo Bills",CAR:"Carolina Panthers",CHI:"Chicago Bears",CIN:"Cincinnati Bengals",CLE:"Cleveland Browns",DAL:"Dallas Cowboys",DEN:"Denver Broncos",DET:"Detroit Lions",GB:"Green Bay Packers",HOU:"Houston Texans",IND:"Indianapolis Colts",JAX:"Jacksonville Jaguars",KC:"Kansas City Chiefs",LAC:"Los Angeles Chargers",LAR:"Los Angeles Rams",LV:"Las Vegas Raiders",MIA:"Miami Dolphins",MIN:"Minnesota Vikings",NE:"New England Patriots",NO:"New Orleans Saints",NYG:"New York Giants",NYJ:"New York Jets",PHI:"Philadelphia Eagles",PIT:"Pittsburgh Steelers",SEA:"Seattle Seahawks",SF:"San Francisco 49ers",TB:"Tampa Bay Buccaneers",TEN:"Tennessee Titans",WAS:"Washington Commanders"};
const OFFENSIVE_LINE_ORDER=["DEN","PHI","TB","IND","CHI","BUF","LAC","KC","ATL","SF","LAR","MIN","NE","PIT","SEA","NO","DAL","LV","DET","CIN","NYJ","ARI","NYG","BAL","MIA","CAR","HOU","GB","TEN","JAX","CLE","WAS"];
function fantasySituationContext(){
  const targetsByPlayer=new Map<string,{player:string;position:string;targets:number;targets_per_game:number}>(),targetRankByPlayer=new Map<string,number>(),handcuffByTeam=new Map<string,{projected_starter:string;handcuff:string}>();
  try{
    const pointer=latest("data/processed/fantasy_context/latest.json"),artifact=latest(pointer.artifact),datasets=artifact.datasets??{};
    const targetRows=(datasets.player_targets_2025?.rows??[]) as {player:string;position:string;targets:number;targets_per_game:number}[];
    for(const row of targetRows)targetsByPlayer.set(row.player,row);
    for(const position of ["WR","TE"]){
      const eligible=targetRows.filter(row=>row.position===position&&row.targets_per_game>0&&row.targets/row.targets_per_game>=8).sort((a,b)=>b.targets_per_game-a.targets_per_game||a.player.localeCompare(b.player));
      eligible.forEach((row,index)=>targetRankByPlayer.set(row.player,index+1));
    }
    for(const row of datasets.rb_handcuffs_2026?.rows??[])handcuffByTeam.set(row.team,row);
  }catch{}
  return {targetsByPlayer,targetRankByPlayer,handcuffByTeam};
}
function rounded(value:number|null|undefined):number|null{return value==null?null:Math.round(value);}
function parseJson<T>(value:string|null,fallback:T):T{try{return value?JSON.parse(value) as T:fallback;}catch{return fallback;}}
function productionLabel(pointsAboveReplacement:number|null|undefined,positionMaximum:number):ProductionLabel{
  const xpar=Number(pointsAboveReplacement??0);if(xpar<=0||positionMaximum<=0)return "Replacement";
  const share=xpar/positionMaximum;
  return share>=.75?"Elite":share>=.5?"Premium":share>=.25?"Starter":"Depth";
}

function syncOperationalFallbackPlayers(service:DraftService):void{
  const productionPointer=latest("data/processed/production_value_model/latest.json"),board=latest(productionPointer.decision_board_json!);
  const modeledIds=new Set((board.players as any[]).map(row=>row.internal_player_id));
  const canonicalPointer=latest("data/processed/canonical_projections/2026/latest.json"),canonical=latest(canonicalPointer.artifact!);
  const adpPointer=latest("data/processed/fantasypros_adp/2026/latest.json"),adp=latest(adpPointer.artifact!);
  const espnPointer=latest("data/processed/espn_salary_cap_values/2026/latest.json"),espn=latest(espnPointer.artifact!);
  const byeByPlayer=new Map((espn.values as any[]).map(row=>[row.internal_player_id,row.bye_week]));
  const byeByTeam=new Map((espn.values as any[]).map(row=>[row.nfl_team,row.bye_week]));
  const insertPlayer=service.db.prepare("INSERT OR IGNORE INTO players(id,display_name,position,nfl_team,identity_status,source_ids_json) VALUES(?,?,?,?,?,?)");
  const findPlayer=service.db.prepare("SELECT id FROM players WHERE id=? OR (display_name=? AND position=? AND nfl_team IS ?) ORDER BY CASE WHEN id=? THEN 0 ELSE 1 END LIMIT 1");
  const upsertFallback=service.db.prepare("INSERT INTO draft_player_pool(draft_id,player_id,status,risk_flags_json,adp_espn,adp_yahoo,bye_week) VALUES(?,?,'available','[\"limited_auction_guidance\"]',?,?,?) ON CONFLICT(draft_id,player_id) DO UPDATE SET status=CASE WHEN draft_player_pool.status='removed' THEN 'available' ELSE draft_player_pool.status END,expected_price=NULL,price_low=NULL,price_high=NULL,draft_probability=NULL,production_value=NULL,expected_surplus=NULL,market_artifact_id=NULL,production_artifact_id=NULL,risk_flags_json='[\"limited_auction_guidance\"]',adp_espn=excluded.adp_espn,adp_yahoo=excluded.adp_yahoo,bye_week=excluded.bye_week");
  const canonicalFantasyProsIds=new Set<number>();
  service.db.transaction(()=>{
    for(const row of canonical.players as any[]){
      const fantasyProsId=Number(row.source_ids?.fantasypros);if(Number.isFinite(fantasyProsId))canonicalFantasyProsIds.add(fantasyProsId);
      if(modeledIds.has(row.internal_player_id))continue;
      insertPlayer.run(row.internal_player_id,row.name,row.position,row.nfl_team,row.internal_player_id.startsWith("provisional:")?"provisional":"stable",JSON.stringify(row.source_ids??{}));
      const player=(findPlayer.get(row.internal_player_id,row.name,row.position,row.nfl_team,row.internal_player_id) as {id:string}|undefined)?.id;if(!player)continue;
      upsertFallback.run(DRAFT_ID,player,row.market_signals?.adp_espn??null,row.market_signals?.adp_yahoo??null,byeByPlayer.get(row.internal_player_id)??byeByTeam.get(row.nfl_team)??null);
    }
    for(const row of adp.players as any[]){
      const best=Math.min(...[row.adp_espn,row.adp_yahoo].filter(Number.isFinite));
      if(!Number.isFinite(best)||best>200||canonicalFantasyProsIds.has(Number(row.fantasypros_id)))continue;
      const position=row.position==="DST"?"DEF":row.position,id=`provisional:fantasypros:${row.fantasypros_id}`;
      insertPlayer.run(id,row.name,position,row.nfl_team??null,"provisional",JSON.stringify({fantasypros:row.fantasypros_id}));
      const player=(findPlayer.get(id,row.name,position,row.nfl_team??null,id) as {id:string}|undefined)?.id;if(!player)continue;
      upsertFallback.run(DRAFT_ID,player,row.adp_espn??null,row.adp_yahoo??null,byeByTeam.get(row.nfl_team)??null);
    }
  })();
}

export function getDraftService():DraftService{
  // Next.js keeps this singleton across hot reloads. If the domain service gains
  // a new command, discard an older in-memory instance so its prototype cannot
  // lag behind the newly loaded server code.
  const cachedService=globalThis.__renegadeDraftService;
  const needsCurrentMigrations=cachedService&&(!cachedService.db.prepare("SELECT 1 FROM sqlite_master WHERE type='table' AND name='draft_nomination_order'").get()||!cachedService.db.prepare("SELECT 1 FROM sqlite_master WHERE type='table' AND name='decision_snapshots'").get()||!cachedService.db.prepare("SELECT 1 FROM schema_migrations WHERE version=13").get());
  if(cachedService&&(typeof cachedService.reassignRosterSlot!=="function"||needsCurrentMigrations)){
    cachedService.db.close();
    globalThis.__renegadeDraftService=undefined;
    decisionCache=null;
  }
  if(globalThis.__renegadeDraftService)return globalThis.__renegadeDraftService;
  mkdirSync(DATA_DIR,{recursive:true});
  const service=DraftService.open(DATABASE_PATH,join(ROOT,"db/migrations/001_initial.sql"));
  if(!service.db.prepare("SELECT id FROM drafts WHERE id=?").get(DRAFT_ID)){
    const production=latest("data/processed/production_value_model/latest.json");
    const owners=latest("data/processed/owner_tendencies/latest.json");
    const espn=latest("data/processed/espn_salary_cap_values/2026/latest.json");
    initializeFromArtifacts(service,{draftId:DRAFT_ID,season:2026,name:"2026 JUGG Auction",decisionBoardPath:production.decision_board_json!,ownerProfilesPath:owners.artifact!,espnSalaryCapPath:espn.artifact!,teamNames:{"George Rodman":"Rodman Renegades"}});
  }else{
    const production=latest("data/processed/production_value_model/latest.json"),board=latest(production.decision_board_json!);
    const ownersPointer=latest("data/processed/owner_tendencies/latest.json"),ownersArtifact=latest(ownersPointer.artifact!);
    const espnPointer=latest("data/processed/espn_salary_cap_values/2026/latest.json"),espn=latest(espnPointer.artifact!);
    const byeByPlayer=new Map((espn.values as any[]).map(row=>[row.internal_player_id,row.bye_week]));
    const byeByTeam=new Map((espn.values as any[]).map(row=>[row.nfl_team,row.bye_week]));
    const artifactHash=(path:string)=>createHash("sha256").update(readFileSync(resolve(ROOT,path))).digest("hex");
    const upsertArtifact=service.db.prepare("INSERT INTO artifact_imports(id,artifact_type,schema_version,build_id,relative_path,sha256,metadata_json) VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET build_id=excluded.build_id,relative_path=excluded.relative_path,sha256=excluded.sha256,metadata_json=excluded.metadata_json,imported_at=CURRENT_TIMESTAMP");
    const upsertPlayer=service.db.prepare("INSERT INTO players(id,display_name,position,nfl_team,identity_status) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET display_name=excluded.display_name,position=excluded.position,nfl_team=excluded.nfl_team,identity_status=excluded.identity_status");
    const upsertPool=service.db.prepare("INSERT INTO draft_player_pool(draft_id,player_id,status,expected_price,price_low,price_high,draft_probability,production_value,expected_surplus,risk_flags_json,market_artifact_id,production_artifact_id,owner_profile_artifact_id,adp_espn,adp_yahoo,bye_week) VALUES(?,?,'available',?,?,?,?,?,?,?,'artifact:decision','artifact:decision','artifact:owners',?,?,?) ON CONFLICT(draft_id,player_id) DO UPDATE SET expected_price=excluded.expected_price,price_low=excluded.price_low,price_high=excluded.price_high,draft_probability=excluded.draft_probability,production_value=excluded.production_value,expected_surplus=excluded.expected_surplus,risk_flags_json=excluded.risk_flags_json,market_artifact_id=excluded.market_artifact_id,production_artifact_id=excluded.production_artifact_id,owner_profile_artifact_id=excluded.owner_profile_artifact_id,adp_espn=excluded.adp_espn,adp_yahoo=excluded.adp_yahoo,bye_week=excluded.bye_week");
    const markRemoved=service.db.prepare("UPDATE draft_player_pool SET status='removed' WHERE draft_id=? AND status='available' AND player_id NOT IN (SELECT value FROM json_each(?))");
    const updateOwner=service.db.prepare("UPDATE owners SET profile_json=?,profile_artifact_id='artifact:owners' WHERE display_name=?");
    service.db.transaction(()=>{
      upsertArtifact.run("artifact:decision","combined_decision_board",1,board.metadata.build_id,production.decision_board_json,artifactHash(production.decision_board_json),JSON.stringify(board.metadata));
      upsertArtifact.run("artifact:owners","owner_tendencies",1,ownersArtifact.metadata.build_id,ownersPointer.artifact,artifactHash(ownersPointer.artifact),JSON.stringify(ownersArtifact.metadata));
      const activeIds:string[]=[];
      for(const row of board.players as any[]){
        activeIds.push(row.internal_player_id);
        upsertPlayer.run(row.internal_player_id,row.player_name,row.position,row.nfl_team,row.internal_player_id.startsWith("provisional:")?"provisional":"stable");
        upsertPool.run(DRAFT_ID,row.internal_player_id,row.expected_jugg_price,row.price_range_low,row.price_range_high,row.draft_probability,row.production_value,row.expected_surplus,JSON.stringify((row.risk_flags||"").split(";").filter(Boolean)),row.adp_espn,row.adp_yahoo,byeByPlayer.get(row.internal_player_id)??byeByTeam.get(row.nfl_team)??null);
      }
      markRemoved.run(DRAFT_ID,JSON.stringify(activeIds));
      for(const profile of ownersArtifact.owners as any[])updateOwner.run(JSON.stringify(profile),profile.owner);
    })();
    service.db.prepare("INSERT OR IGNORE INTO draft_strategy(draft_id,strategy_json) VALUES(?,?)").run(DRAFT_ID,JSON.stringify(DEFAULT_STRATEGY));
  }
  syncOperationalFallbackPlayers(service);
  importFantasyAnalysis(service,ROOT);
  importFantasyResearchSynthesis(service,ROOT);
  globalThis.__renegadeDraftService=service;
  return service;
}

function clamp(value:number,minimum:number,maximum:number){return Math.max(minimum,Math.min(maximum,value));}
function marketContext(service:DraftService){
  const sales=service.db.prepare(`SELECT s.price,p.position,pool.expected_price expectedPrice FROM sales s JOIN players p ON p.id=s.player_id JOIN draft_player_pool pool ON pool.draft_id=s.draft_id AND pool.player_id=s.player_id WHERE s.draft_id=? AND s.voided_event_id IS NULL AND pool.expected_price>0`).all(DRAFT_ID) as {price:number;position:string;expectedPrice:number}[];
  const multiplier=(rows:typeof sales,prior:number)=>{if(!rows.length)return 1;const ratio=rows.reduce((sum,row)=>sum+row.price,0)/rows.reduce((sum,row)=>sum+row.expectedPrice,0);const weight=rows.length/(rows.length+prior);return clamp(1+(ratio-1)*weight,.75,1.35);};
  const globalMultiplier=multiplier(sales,8),positions:Record<string,{salesCount:number;multiplier:number}>={};
  for(const position of ["QB","RB","WR","TE","K","DEF"]){const rows=sales.filter(row=>row.position===position);const positional=multiplier(rows,5);positions[position]={salesCount:rows.length,multiplier:rows.length?clamp(globalMultiplier*.4+positional*.6,.75,1.35):globalMultiplier};}
  return {salesCount:sales.length,globalMultiplier,positions};
}

function ownerSignal(profile:OwnerProfile|null,position:string,playerId:string):string|null{
  if(!profile)return null;
  const repeat=profile.repeat_players?.find(row=>row.internal_player_id===playerId);
  if(repeat)return `${profile.owner} drafted this player in ${repeat.times_drafted} prior seasons.`;
  const positionSignal=profile.positions?.[position];
  if(positionSignal&&positionSignal.signal!=="neutral"&&positionSignal.direction_consistency>=0.66)return `${profile.owner} historically ${positionSignal.signal} ${position}s.`;
  return null;
}

function latestDecisionChange(service:DraftService){
  const rows=service.db.prepare("SELECT id,trigger_type triggerType,snapshot_json snapshotJson,created_at createdAt FROM decision_snapshots WHERE draft_id=? ORDER BY created_at DESC,rowid DESC LIMIT 2").all(DRAFT_ID) as {id:string;triggerType:string;snapshotJson:string;createdAt:string}[];
  if(!rows[0])return null;
  const current=parseJson<any>(rows[0].snapshotJson,{}),previous=rows[1]?parseJson<any>(rows[1].snapshotJson,{}):null;
  const top=current.upcomingTargets?.[0],priorTop=previous?.upcomingTargets?.[0],reasons:string[]=[];
  if(top&&priorTop&&top.playerId!==priorTop.playerId)reasons.push(`${top.name} moved ahead of ${priorTop.name} as the next priority.`);
  else if(top)reasons.push(`${top.name} remains the top upcoming target around $${top.targetPrice}.`);
  const equity=current.renegadesEquity,priorEquity=previous?.renegadesEquity;
  if(typeof equity==="number"&&typeof priorEquity==="number"&&Math.abs(equity-priorEquity)>=.0005)reasons.push(`Renegades championship outlook moved from ${(priorEquity*100).toFixed(1)}% to ${(equity*100).toFixed(1)}%.`);
  const currentCeiling=current.nomination?.committedCeiling,priorCeiling=previous?.nomination?.committedCeiling;
  if(currentCeiling&&priorCeiling&&currentCeiling!==priorCeiling)reasons.push(`The walk-away price changed from $${priorCeiling} to $${currentCeiling}.`);
  const headline=rows[0].triggerType==="nominate"&&current.nomination?`Plan set for ${current.nomination.name} with a $${current.nomination.committedCeiling} walk-away price.`:rows[0].triggerType==="sale"?`Draft roadmap recalculated after the latest sale.`:rows[0].triggerType==="commitCeiling"?`Walk-away price updated deliberately.`:rows[0].triggerType==="playerPreference"||rows[0].triggerType==="updateStrategy"?`Personal strategy recalculated the roadmap.`:`Draft advice recalculated after ${rows[0].triggerType}.`;
  return {snapshotId:rows[0].id,triggerType:rows[0].triggerType,headline,reasons,createdAt:rows[0].createdAt};
}

function recordDecisionSnapshot(service:DraftService,view:any,triggerType:string,triggerKey:string){
  const renegadesEquity=view.leaderboard?.find((row:any)=>row.name==="Rodman Renegades")?.championshipEquity??null;
  const snapshot={stateVersion:view.draft.stateVersion,renegadesEquity,renegades:{remainingBudget:view.renegades?.remainingBudget,openSlots:view.renegades?.openSlots},nomination:view.currentNomination?{playerId:view.currentNomination.playerId,name:view.currentNomination.name,recommendedCeiling:view.currentNomination.decisionPlan?.recommendedCeiling,committedCeiling:view.currentNomination.decisionPlan?.committedCeiling,band:view.currentNomination.championshipDecision?.band}:null,upcomingTargets:view.upcomingTargets,tierSupply:Object.fromEntries(view.players.filter((player:any)=>player.status==="available"||player.status==="nominated").reduce((map:Map<string,number>,player:any)=>{const key=`${player.position}:${player.productionTier??"?"}`;map.set(key,(map.get(key)??0)+1);return map;},new Map<string,number>()))};
  service.db.prepare("INSERT OR IGNORE INTO decision_snapshots(id,draft_id,state_version,trigger_type,trigger_key,snapshot_json,created_at) VALUES(?,?,?,?,?,?,?)").run(randomUUID(),DRAFT_ID,view.draft.stateVersion,triggerType,triggerKey,JSON.stringify(snapshot),new Date().toISOString());
}

export function readDraftRoom(){
  const service=getDraftService();
  const draft=service.db.prepare("SELECT id,status,state_version stateVersion FROM drafts WHERE id=?").get(DRAFT_ID) as any;
  const storedStrategy=parseJson<Partial<Strategy>>((service.db.prepare("SELECT strategy_json strategyJson FROM draft_strategy WHERE draft_id=?").get(DRAFT_ID) as any)?.strategyJson,DEFAULT_STRATEGY);
  const strategy:Strategy={...DEFAULT_STRATEGY,...storedStrategy,teamPreferences:storedStrategy.teamPreferences??[],situations:storedStrategy.situations??[]};
  const market=marketContext(service);
  const productionPointer=latest("data/processed/production_value_model/latest.json"),decisionBoard=latest(productionPointer.decision_board_json!);
  const canonicalPointer=latest("data/processed/canonical_projections/2026/latest.json"),canonicalProjections=latest(canonicalPointer.artifact!);
  const projectedById=new Map<string,number|null>((canonicalProjections.players as any[]).map(row=>[row.internal_player_id,row.fantasypros?.league_projected_points==null?null:Number(row.fantasypros.league_projected_points)]));
  for(const row of decisionBoard.players as any[])projectedById.set(row.internal_player_id,Number(row.projected_points??0));
  const productionById=new Map((decisionBoard.players as any[]).map(row=>[row.internal_player_id,row]));
  const fantasyProsContext=fantasyProsContextByPlayer();
  const previousTeamByPlayer=priorTeamByPlayer();
  const depthChartsByTeam=teamDepthCharts();
  const situationContext=fantasySituationContext();
  const maximumXparByPosition=new Map<string,number>();
  for(const row of decisionBoard.players as any[])maximumXparByPosition.set(row.position,Math.max(maximumXparByPosition.get(row.position)??0,Number(row.points_above_replacement??0)));
  const renegadeId=(service.db.prepare("SELECT id FROM teams WHERE draft_id=? AND display_name='Rodman Renegades'").get(DRAFT_ID) as any)?.id;
  const byeCounts=new Map<number,number>();
  for(const row of service.db.prepare(`SELECT pool.bye_week byeWeek FROM roster_slots rs JOIN draft_player_pool pool ON pool.draft_id=? AND pool.player_id=rs.player_id WHERE rs.team_id=? AND rs.player_id IS NOT NULL`).all(DRAFT_ID,renegadeId) as {byeWeek:number|null}[])if(row.byeWeek)byeCounts.set(row.byeWeek,(byeCounts.get(row.byeWeek)??0)+1);
  const rawPlayers=service.db.prepare(`SELECT p.id,p.display_name name,p.position,p.nfl_team nflTeam,pool.status,pool.expected_price expectedPrice,pool.price_low priceLow,pool.price_high priceHigh,pool.production_value productionValue,pool.expected_surplus edge,pool.draft_probability draftProbability,pool.risk_flags_json riskFlags,pool.adp_espn adpEspn,pool.adp_yahoo adpYahoo,pool.bye_week byeWeek,pref.preference,pref.premium preferencePremium,pref.note preferenceNote,s.price salePrice,winner_owner.display_name draftedBy FROM draft_player_pool pool JOIN players p ON p.id=pool.player_id LEFT JOIN player_preferences pref ON pref.draft_id=pool.draft_id AND pref.player_id=pool.player_id LEFT JOIN sales s ON s.draft_id=pool.draft_id AND s.player_id=pool.player_id AND s.voided_event_id IS NULL LEFT JOIN teams winner ON winner.id=s.winner_team_id LEFT JOIN owners winner_owner ON winner_owner.id=winner.owner_id WHERE pool.draft_id=? ORDER BY pool.expected_price DESC,p.display_name`).all(DRAFT_ID) as any[];
  const fantasyAnalysisRows=service.db.prepare(`SELECT t.player_id playerId,t.label,t.sentiment,t.summary,t.rationale,t.risks_json risksJson,s.id sourceId,s.source_key sourceKey,s.title sourceTitle,s.author,s.url,s.published_at publishedAt FROM fantasy_player_takeaways t JOIN fantasy_analysis_sources s ON s.id=t.source_id WHERE s.season=? ORDER BY s.published_at DESC,s.title`).all(2026) as any[];
  const fantasyAnalysisByPlayer=new Map<string,any[]>();
  for(const row of fantasyAnalysisRows){const entries=fantasyAnalysisByPlayer.get(row.playerId)??[];entries.push({...row,risks:parseJson<string[]>(row.risksJson,[]),risksJson:undefined});fantasyAnalysisByPlayer.set(row.playerId,entries);}
  const analysisOverrides=new Map((service.db.prepare("SELECT player_id playerId,override_value overrideValue FROM fantasy_analysis_overrides WHERE draft_id=?").all(DRAFT_ID) as {playerId:string;overrideValue:"target"|"avoid"|"off"}[]).map(row=>[row.playerId,row.overrideValue]));
  const analysisTagOverrides=new Map<string,Map<string,boolean>>();
  for(const row of service.db.prepare("SELECT player_id playerId,tag,enabled FROM fantasy_analysis_tag_overrides WHERE draft_id=?").all(DRAFT_ID) as {playerId:string;tag:string;enabled:number}[]){const values=analysisTagOverrides.get(row.playerId)??new Map<string,boolean>();values.set(row.tag,Boolean(row.enabled));analysisTagOverrides.set(row.playerId,values);}
  const aiSummaries=new Map((service.db.prepare("SELECT player_id playerId,summary cardSummary,full_writeup fullWriteup,pros_summary prosSummary,cons_summary consSummary,source_ids_json sourceIdsJson,input_hash inputHash,prompt_version promptVersion,model,generated_at generatedAt FROM fantasy_player_summaries").all() as any[]).map(row=>[row.playerId,{cardSummary:row.cardSummary,fullWriteup:row.fullWriteup,prosSummary:row.prosSummary,consSummary:row.consSummary,sourceIds:parseJson<string[]>(row.sourceIdsJson,[]),inputHash:row.inputHash,promptVersion:row.promptVersion,model:row.model,generatedAt:row.generatedAt}]));
  const pendingSummaryPlayers=new Set<string>(),pendingSummarySources=new Set<string>();let pendingSummaryTakeaways=0;
  for(const [playerId,entries] of fantasyAnalysisByPlayer){const included=new Set(aiSummaries.get(playerId)?.sourceIds??[]);for(const entry of entries){if(included.has(entry.sourceId))continue;pendingSummaryPlayers.add(playerId);pendingSummarySources.add(entry.sourceId);pendingSummaryTakeaways++;}}
  const summaryGeneratedAt=[...aiSummaries.values()].map(row=>row.generatedAt).sort().at(-1)??null;
  const analysisConsensus=(playerId:string)=>{
    const entries=fantasyAnalysisByPlayer.get(playerId)??[],seen=new Set<string>(),independent:any[]=[];
    for(const entry of entries){const analyst=(entry.author||entry.sourceId).trim().toLowerCase();if(seen.has(analyst))continue;seen.add(analyst);independent.push(entry);}
    const positive=independent.filter(entry=>entry.sentiment==="positive"),negative=independent.filter(entry=>entry.sentiment==="negative");
    const derivedAction=positive.length>negative.length?"target":negative.length>positive.length?"avoid":null;
    const override=analysisOverrides.get(playerId)??null,action=override==="off"?null:override??derivedAction;
    const derivedTags=[...new Set(entries.map(entry=>entry.label).filter(label=>["sleeper","breakout","value","bust"].includes(label)))];
    const tagOverrideMap=analysisTagOverrides.get(playerId)??new Map<string,boolean>(),tagOverrides=Object.fromEntries(tagOverrideMap),tags=["sleeper","breakout","value","bust"].filter(tag=>tagOverrideMap.get(tag)??derivedTags.includes(tag));
    const sourceNames=[...new Set(entries.map(entry=>entry.sourceKey==="yahoo_sports"?"Yahoo Sports":entry.sourceKey==="espn"?"ESPN":entry.sourceKey))];
    const distinct=(values:(string|null|undefined)[])=>[...new Map(values.filter((value):value is string=>Boolean(value?.trim())).map(value=>[value.trim().toLowerCase(),value.trim()])).values()];
    const pros=distinct(positive.map(entry=>entry.summary)).slice(0,4);
    const cons=distinct([...negative.map(entry=>entry.summary),...independent.flatMap(entry=>entry.risks)]).slice(0,4);
    return {action,derivedAction,override,tags,derivedTags,tagOverrides,positiveCount:positive.length,negativeCount:negative.length,independentOpinionCount:independent.length,pros,cons,commonCase:pros[0]??null,mainConcern:cons[0]??null,sources:sourceNames,aiSummary:aiSummaries.get(playerId)??null};
  };
  const basePlayers=rawPlayers.map(row=>{
    const production=productionById.get(row.id) as any;
    const multiplier=market.positions[row.position]?.multiplier??market.globalMultiplier,liveExpected=row.expectedPrice==null?null:rounded(row.expectedPrice*multiplier);
    const reasons:string[]=[],riskFlags=parseJson<string[]>(row.riskFlags,[]);let adjustment=0;
    if(row.preference==="target"){adjustment+=row.preferencePremium??strategy.targetPremium;reasons.push(`Target premium +$${row.preferencePremium??strategy.targetPremium}`);}
    if(row.preference==="avoid"){adjustment-=Math.max(4,Math.abs(row.preferencePremium??0));reasons.push("Player preference: avoid if similarly valued options remain");}
    for(const rule of strategy.teamPreferences.filter(rule=>rule.team===row.nflTeam&&(rule.position==="ALL"||rule.position===row.position))){const amount=Math.abs(rule.adjustment||2)*(rule.preference==="prefer"?1:-1);adjustment+=amount;reasons.push(`${rule.preference==="prefer"?"Preferred":"Cautious"} ${row.nflTeam}${rule.position==="ALL"?"":` ${rule.position}`} situation${rule.note?`: ${rule.note}`:""}`);}
    const sameBye=row.byeWeek?(byeCounts.get(row.byeWeek)??0):0;
    if(strategy.byeWeekMode!=="ignore"&&sameBye>=strategy.maxSameBye){const penalty=strategy.byeWeekMode==="strict"?5:2;adjustment-=penalty;reasons.push(`${sameBye} rostered players already have Week ${row.byeWeek} bye`);}
    if(strategy.riskTolerance==="conservative"&&riskFlags.length){adjustment-=2;reasons.push("Conservative risk adjustment");}
    if(strategy.riskTolerance==="aggressive"&&(row.edge??0)>5){adjustment+=1;reasons.push("Aggressive value-upside adjustment");}
    adjustment=clamp(adjustment,-12,12);
    const strategyValue=row.productionValue==null?null:rounded(Math.max(0,row.productionValue+adjustment));
    const situationSignals:SituationSignal[]=[];
    const lineRank=row.nflTeam?OFFENSIVE_LINE_ORDER.indexOf(row.nflTeam)+1:0;
    if(lineRank>0&&lineRank<=10)situationSignals.push({key:"offensive_line",tone:"positive",text:`Plays behind a top-10 offensive line (ranked ${lineRank} of 32).`,priority:88});
    else if(lineRank>=23)situationSignals.push({key:"offensive_line",tone:"negative",text:`Plays behind a bottom-10 offensive line (ranked ${lineRank} of 32).`,priority:88});
    const usage=situationContext.targetsByPlayer.get(row.name),targetRank=situationContext.targetRankByPlayer.get(row.name);
    if(usage&&targetRank&&["WR","TE"].includes(row.position)){
      const games=usage.targets_per_game>0?usage.targets/usage.targets_per_game:0;
      if(targetRank<=12)situationSignals.push({key:"target_volume",tone:"positive",text:`Had top-12 ${row.position} target volume last season (${targetRank}${targetRank===1?"st":targetRank===2?"nd":targetRank===3?"rd":"th"} at the position per game).`,priority:86});
      else if(games>=8&&((row.position==="WR"&&usage.targets_per_game<2)||(row.position==="TE"&&usage.targets_per_game<1.5)))situationSignals.push({key:"target_volume",tone:"negative",text:`Had limited target volume last season for a ${row.position}.`,priority:82});
    }
    const teamName=row.nflTeam?TEAM_NAMES[row.nflTeam]:undefined,backfield=teamName?situationContext.handcuffByTeam.get(teamName):undefined;
    if(row.position==="RB"&&backfield?.projected_starter===row.name)situationSignals.push({key:"backfield_role",tone:"positive",text:"Listed as the projected starter in his backfield.",priority:84});
    else if(row.position==="RB"&&backfield?.handcuff===row.name)situationSignals.push({key:"backfield_role",tone:"negative",text:`Listed as the primary handcuff behind ${backfield!.projected_starter}.`,priority:84});
    const entries=fantasyAnalysisByPlayer.get(row.id)??[];
    const positiveRoleText=entries.filter(entry=>entry.sentiment==="positive").map(entry=>`${entry.summary} ${entry.rationale}`).join(" ").toLowerCase();
    const concernText=entries.flatMap(entry=>entry.risks??[]).concat(entries.filter(entry=>entry.sentiment==="negative").map(entry=>entry.summary)).join(" ").toLowerCase();
    if(row.position==="RB"&&/(bell.?cow|workhorse|three-down|feature(?:d)? (?:back|role)|clear lead role|lead-back role|300\+? (?:touch|opportun))/i.test(positiveRoleText))situationSignals.push({key:"workload_role",tone:"positive",text:"Current role reports support a lead or bell-cow workload.",priority:91});
    else if(row.position==="RB"&&/(committee|timeshare|shared role|backup role|limited standalone|split(?:ting)? (?:the )?(?:work|backfield))/i.test(concernText))situationSignals.push({key:"workload_role",tone:"negative",text:"A committee or limited standalone workload is a meaningful concern.",priority:91});
    if(row.position==="RB"&&/(goal-line|short-yardage|inside the 5|red-zone work)/i.test(positiveRoleText))situationSignals.push({key:"goal_line_role",tone:"positive",text:"Current role evidence supports meaningful goal-line work.",priority:89});
    else if(row.position==="RB"&&/(limited goal-line|goal-line competition|few goal-line|no goal-line|lacks? goal-line|goal-line role.*(?:uncertain|capped))/i.test(concernText))situationSignals.push({key:"goal_line_role",tone:"negative",text:"Goal-line opportunity is limited or contested.",priority:89});
    const guidanceLevel=production?"modeled":projectedById.get(row.id)!=null?"limited":"adp_only";
    return {...row,guidanceLevel,projectedPoints:projectedById.get(row.id)??null,expectedPrice:rounded(row.expectedPrice),priceLow:rounded(row.priceLow),priceHigh:rounded(row.priceHigh),liveExpectedPrice:liveExpected,livePriceLow:row.priceLow==null?null:rounded(row.priceLow*multiplier),livePriceHigh:row.priceHigh==null?null:rounded(row.priceHigh*multiplier),marketMultiplier:Number(multiplier.toFixed(3)),marketAdp:rounded(([row.adpEspn,row.adpYahoo].filter(Number.isFinite) as number[]).reduce((sum,value)=>sum+value,0)/([row.adpEspn,row.adpYahoo].filter(Number.isFinite).length||1))||null,productionValue:rounded(row.productionValue),edge:rounded(row.edge),liveEdge:strategyValue==null||liveExpected==null?null:strategyValue-liveExpected,strategyValue,strategyReasons:reasons,riskFlags,situationSignals,
      positionRank:production?.position_rank??null,replacementPoints:production?.replacement_points??null,pointsAboveReplacement:production?.points_above_replacement??null,birthDate:production?.birth_date??null,yearsOfExperience:production?.years_of_experience??null,
      productionLabel:production?productionLabel(production.points_above_replacement,maximumXparByPosition.get(row.position)??0):null,
      productionTier:production?.production_tier??null,productionTierSize:production?.production_tier_size??null,productionTierHigh:production?.production_tier_high??null,productionTierLow:production?.production_tier_low??null,
      auctionTier:production?.auction_tier??null,auctionTierSize:production?.auction_tier_size??null,auctionTierHigh:production?.auction_tier_high??null,auctionTierLow:production?.auction_tier_low??null,
      lastSeasonStatLine:production?.last_season_stat_line??null,historicalStatLines:production?.historical_stat_lines??(production?.last_season_stat_line?[production.last_season_stat_line]:[]),projectedStatLine:production?.projected_stat_line??null,
      fantasyAnalysis:fantasyAnalysisByPlayer.get(row.id)??[],analystConsensus:analysisConsensus(row.id),injury:fantasyProsContext.get(row.id)?.injury??null,recentNews:fantasyProsContext.get(row.id)?.recentNews??[],teamDepthChart:depthChartsByTeam.get(row.nflTeam)??null,offensiveLineRank:lineRank||null,previousNflTeam:previousTeamByPlayer.get(row.id)??null};
  });
  const quarterbackByTeam=new Map<string,(typeof basePlayers)[number]>();
  for(const quarterback of basePlayers.filter(player=>player.position==="QB"&&player.nflTeam).sort((a,b)=>(a.positionRank??999)-(b.positionRank??999)))if(!quarterbackByTeam.has(quarterback.nflTeam))quarterbackByTeam.set(quarterback.nflTeam,quarterback);
  const players=basePlayers.map(player=>{
    const situationSignals=[...player.situationSignals] as SituationSignal[],quarterback=quarterbackByTeam.get(player.nflTeam);
    if(["RB","WR","TE"].includes(player.position)&&quarterback?.positionRank!=null){
      if(quarterback.positionRank<=8)situationSignals.push({key:"quarterback_quality",tone:"positive",text:`Plays with a top-eight fantasy quarterback in ${quarterback.name}.`,priority:87});
      else if(quarterback.positionRank>=25)situationSignals.push({key:"quarterback_quality",tone:"negative",text:`Plays with a bottom-eight projected fantasy quarterback in ${quarterback.name}.`,priority:87});
    }
    return {...player,situationSignals};
  });
  const comparableAlternatives=(focus:any)=>{
    const focusPrice=Math.max(1,focus.liveExpectedPrice??focus.expectedPrice??1),focusPoints=Math.max(1,focus.projectedPoints??1);
    const score=(candidate:any)=>.3*Math.abs((candidate.productionTier??99)-(focus.productionTier??99))+Math.abs(Math.log(Math.max(1,candidate.liveExpectedPrice??candidate.expectedPrice??1)/focusPrice))+.65*Math.abs(Math.log(Math.max(1,candidate.projectedPoints??1)/focusPoints));
    return players.filter(player=>player.guidanceLevel==="modeled"&&player.status==="available"&&player.id!==focus.id&&player.position===focus.position).sort((a,b)=>score(a)-score(b)||(b.liveExpectedPrice??0)-(a.liveExpectedPrice??0)).slice(0,3).map(player=>({id:player.id,name:player.name,nflTeam:player.nflTeam,projectedPoints:player.projectedPoints,pointsAboveReplacement:player.pointsAboveReplacement,productionTier:player.productionTier,liveExpectedPrice:player.liveExpectedPrice??player.expectedPrice,productionLabel:player.productionLabel}));
  };
  const boardPlayers=players.map(player=>({...player,alternatives:player.status==="sold"?[]:comparableAlternatives(player)}));
  const teams=(service.db.prepare(`SELECT t.id,t.display_name name,o.display_name owner,s.remaining_budget remainingBudget,s.open_slot_count openSlots,s.rostered_player_count rosteredCount,d.minimum_bid minimumBid,o.profile_json profileJson FROM teams t JOIN owners o ON o.id=t.owner_id JOIN team_draft_state s ON s.team_id=t.id JOIN drafts d ON d.id=t.draft_id WHERE t.draft_id=? ORDER BY CASE WHEN t.display_name='Rodman Renegades' THEN 0 ELSE 1 END,s.remaining_budget DESC`).all(DRAFT_ID) as any[]).map(row=>({...row,maxBid:row.remainingBudget-(row.openSlots-1)*row.minimumBid,profile:parseJson<OwnerProfile|null>(row.profileJson,null),profileJson:undefined}));
  const nominationOrderCount=(service.db.prepare("SELECT COUNT(*) count FROM draft_nomination_order WHERE draft_id=?").get(DRAFT_ID) as {count:number}).count;
  if(nominationOrderCount===0){const alphabetical=[...teams].sort((a,b)=>a.owner.localeCompare(b.owner,undefined,{sensitivity:"base"}));const insert=service.db.prepare("INSERT INTO draft_nomination_order(draft_id,team_id,ordinal) VALUES(?,?,?)");service.db.transaction(()=>alphabetical.forEach((team,index)=>insert.run(DRAFT_ID,team.id,index+1)))();}
  const nominationOrder=service.db.prepare(`WITH active_completions AS (SELECT c.team_id,c.completed_at,e.sequence,ROW_NUMBER() OVER (ORDER BY e.sequence) waiverPriority FROM team_draft_completions c JOIN draft_events e ON e.id=c.completed_event_id WHERE c.draft_id=? AND c.voided_event_id IS NULL) SELECT no.team_id teamId,no.ordinal,t.display_name team,o.display_name owner,s.open_slot_count openSlots,ac.completed_at completedAt,ac.waiverPriority FROM draft_nomination_order no JOIN teams t ON t.id=no.team_id JOIN owners o ON o.id=t.owner_id JOIN team_draft_state s ON s.team_id=t.id LEFT JOIN active_completions ac ON ac.team_id=t.id WHERE no.draft_id=? ORDER BY no.ordinal`).all(DRAFT_ID,DRAFT_ID) as any[];
  const lastNominator=(service.db.prepare(`SELECT n.nominated_by_team_id teamId FROM nominations n JOIN draft_events e ON e.id=n.opened_event_id WHERE n.draft_id=? AND n.nominated_by_team_id IS NOT NULL ORDER BY e.sequence DESC LIMIT 1`).get(DRAFT_ID) as {teamId:string}|undefined)?.teamId;
  const lastIndex=nominationOrder.findIndex(row=>row.teamId===lastNominator);let nextNominatorTeamId:string|null=null;
  for(let offset=1;offset<=nominationOrder.length;offset++){const candidate=nominationOrder[(lastIndex+offset+nominationOrder.length)%nominationOrder.length];if(candidate&&candidate.openSlots>0){nextNominatorTeamId=candidate.teamId;break;}}
  const nomination=service.db.prepare(`SELECT n.id nominationId,p.id playerId,p.display_name name,p.position,p.nfl_team nflTeam,pool.expected_price expectedPrice,pool.price_low priceLow,pool.price_high priceHigh,pool.production_value productionValue,pool.expected_surplus edge,pool.risk_flags_json riskFlags,t.id nominatorTeamId,o.display_name nominator FROM nominations n JOIN players p ON p.id=n.player_id JOIN draft_player_pool pool ON pool.draft_id=n.draft_id AND pool.player_id=n.player_id LEFT JOIN teams t ON t.id=n.nominated_by_team_id LEFT JOIN owners o ON o.id=t.owner_id WHERE n.draft_id=? AND n.status='open'`).get(DRAFT_ID) as any;
  let currentNomination:any=null;
  if(nomination){
    const nominatorTeam=teams.find(team=>team.id===nomination.nominatorTeamId);
    const enriched=players.find(player=>player.id===nomination.playerId)!;
    const competition=teams.filter(team=>team.name!=="Rodman Renegades"&&team.maxBid>=Math.max(1,enriched.liveExpectedPrice??enriched.expectedPrice??1)).slice(0,4).map(team=>({id:team.id,name:team.owner,maxBid:team.maxBid,signal:ownerSignal(team.profile,nomination.position,nomination.playerId)}));
    const alternatives=comparableAlternatives(enriched);
    currentNomination={...enriched,nominationId:nomination.nominationId,playerId:nomination.playerId,nominator:nomination.nominator,nominatorTeamId:nomination.nominatorTeamId,ownerSignal:ownerSignal(nominatorTeam?.profile??null,nomination.position,nomination.playerId),competition,alternatives};
  }
  const recentSales=service.db.prepare(`SELECT s.id,ROW_NUMBER() OVER (ORDER BY e.sequence) pick,p.display_name player,o.display_name team,s.price,s.recorded_at recordedAt FROM sales s JOIN draft_events e ON e.id=s.recorded_event_id JOIN players p ON p.id=s.player_id JOIN teams t ON t.id=s.winner_team_id JOIN owners o ON o.id=t.owner_id WHERE s.draft_id=? AND s.voided_event_id IS NULL ORDER BY e.sequence DESC`).all(DRAFT_ID);
  const renegades=teams.find(team=>team.name==="Rodman Renegades")??teams[0];
  const rawRosters=service.db.prepare(`SELECT rs.id slotId,rs.team_id teamId,rs.slot_type slotType,rs.ordinal,rs.eligible_positions_json eligiblePositionsJson,p.id playerId,p.display_name player,p.position,pool.bye_week byeWeek,s.price pricePaid FROM roster_slots rs JOIN teams t ON t.id=rs.team_id LEFT JOIN players p ON p.id=rs.player_id LEFT JOIN draft_player_pool pool ON pool.draft_id=? AND pool.player_id=rs.player_id LEFT JOIN sales s ON s.id=rs.filled_sale_id AND s.voided_event_id IS NULL WHERE t.draft_id=? ORDER BY t.display_name,CASE rs.slot_type WHEN 'QB' THEN 1 WHEN 'WR' THEN 2 WHEN 'RB' THEN 3 WHEN 'TE' THEN 4 WHEN 'WR_RB' THEN 5 WHEN 'WR_RB_TE' THEN 6 WHEN 'DEF' THEN 7 WHEN 'K' THEN 8 ELSE 9 END,rs.ordinal`).all(DRAFT_ID,DRAFT_ID) as any[];
  const enrichedRosters=rawRosters.map(row=>{const production=productionById.get(row.playerId) as any;const rank=Number(production?.position_rank)||null;return {...row,eligiblePositions:parseJson<Position[]>(row.eligiblePositionsJson,[]),eligiblePositionsJson:undefined,positionRank:rank,pointsAboveReplacement:production?.points_above_replacement==null?null:Number(production.points_above_replacement),productionLabel:row.playerId?productionLabel(production?.points_above_replacement,maximumXparByPosition.get(row.position)??0):null};});
  const teamRosters=Object.fromEntries(teams.map(team=>[team.id,enrichedRosters.filter(row=>row.teamId===team.id)]));
  const roster=renegades?teamRosters[renegades.id]??[]:[];
  const decisionPlayers=new Map<string,DecisionPlayer>(players.map(player=>[player.id,{id:player.id,name:player.name,position:player.position as Position,projectedPoints:player.projectedPoints??0,
    expectedPrice:Math.max(1,player.liveExpectedPrice??player.expectedPrice??1),priceLow:Math.max(1,player.livePriceLow??player.priceLow??1),priceHigh:Math.max(1,player.livePriceHigh??player.priceHigh??1),
    productionTier:player.productionTier??undefined,auctionTier:player.auctionTier??undefined,pointsAboveReplacement:player.pointsAboveReplacement??undefined,replacementPoints:player.replacementPoints??undefined,
    strategyValue:player.strategyValue??undefined,strategyAdjustment:player.strategyValue!=null&&player.productionValue!=null?player.strategyValue-player.productionValue:0,preference:player.preference,strategyReasons:player.strategyReasons} as DecisionPlayer]));
  const rosterRows=service.db.prepare(`SELECT rs.team_id teamId,rs.player_id playerId FROM roster_slots rs JOIN teams t ON t.id=rs.team_id WHERE t.draft_id=? AND rs.player_id IS NOT NULL`).all(DRAFT_ID) as {teamId:string;playerId:string}[];
  const decisionTeams:DecisionTeam[]=teams.map(team=>({id:team.id,name:team.name,owner:team.owner,remainingBudget:team.remainingBudget,openSlots:team.openSlots,
    roster:rosterRows.filter(row=>row.teamId===team.id).map(row=>decisionPlayers.get(row.playerId)).filter((player):player is DecisionPlayer=>Boolean(player))}));
  const availableDecisionPlayers=players.filter(player=>player.guidanceLevel==="modeled"&&(player.status==="available"||player.status==="nominated")).map(player=>decisionPlayers.get(player.id)).filter((player):player is DecisionPlayer=>Boolean(player));
  const roadmapPlayers=players.filter(player=>player.guidanceLevel==="modeled"&&player.status==="available").map(player=>decisionPlayers.get(player.id)).filter((player):player is DecisionPlayer=>Boolean(player));
  const cacheKey=`${draft.stateVersion}:${JSON.stringify(strategy)}`;
  if(!decisionCache||decisionCache.key!==cacheKey){
    const roadmap=renegades?draftRoadmap(decisionTeams,renegades.id,roadmapPlayers,renegades.maxBid):{targets:[],impacts:[]};
    decisionCache={key:cacheKey,leaderboard:liveLeaderboard(decisionTeams,availableDecisionPlayers),championshipDecision:currentNomination&&currentNomination.guidanceLevel==="modeled"&&renegades?nominationDecision(decisionTeams,renegades.id,availableDecisionPlayers,currentNomination.playerId,renegades.maxBid):null,...roadmap};
  }
  const {leaderboard,championshipDecision,targets,impacts}=decisionCache;
  const targetByPlayerId=new Map(targets.map(target=>[target.playerId,target]));
  const impactByPlayerId=new Map(impacts.map(impact=>[impact.playerId,impact]));
  if(currentNomination&&championshipDecision){
    const labels:Record<string,string>={strong_pursue:"Great Add",lean_pursue:"Good Add",neutral:"Neutral",lean_pass:"Poor Add",strong_pass:"Bad Add"};
    impactByPlayerId.set(currentNomination.playerId,{playerId:currentNomination.playerId,price:currentNomination.liveExpectedPrice,band:championshipDecision.band,label:labels[championshipDecision.band],expectedEquityDelta:championshipDecision.medianDelta,scenarioSupport:championshipDecision.support,role:"Current nomination",summary:`At $${currentNomination.liveExpectedPrice}, buying creates a better projected final roster in ${Math.round(championshipDecision.support*9)} of 9 tested draft paths. ${championshipDecision.explanation}`});
  }
  for(const player of boardPlayers){
    const target=targetByPlayerId.get(player.id);
    const decisionCeiling=currentNomination?.playerId===player.id?championshipDecision?.recommendedMax??null:target?.walkawayCeiling??null;
    player.decisionCeiling=decisionCeiling;
    player.decisionEdge=decisionCeiling==null||player.liveExpectedPrice==null?null:decisionCeiling-player.liveExpectedPrice;
    player.liveEdge=player.decisionEdge;
    player.draftImpact=impactByPlayerId.get(player.id)??null;
  }
  let decisionPlan:any=null;
  if(currentNomination&&currentNomination.guidanceLevel==="modeled"&&renegades){
    const recommendedCeiling=Math.max(1,championshipDecision?.recommendedMax??1);
    const existingPlan=service.db.prepare("SELECT recommended_ceiling recommendedCeiling,committed_ceiling committedCeiling,adjustment_reason adjustmentReason FROM nomination_decision_plans WHERE nomination_id=?").get(currentNomination.nominationId) as any;
    if(!existingPlan)service.db.prepare("INSERT INTO nomination_decision_plans(nomination_id,draft_id,player_id,recommended_ceiling,committed_ceiling) VALUES(?,?,?,?,?)").run(currentNomination.nominationId,DRAFT_ID,currentNomination.playerId,recommendedCeiling,recommendedCeiling);
    else if(existingPlan.adjustmentReason==null&&existingPlan.committedCeiling===existingPlan.recommendedCeiling)service.db.prepare("UPDATE nomination_decision_plans SET recommended_ceiling=?,committed_ceiling=?,updated_at=CURRENT_TIMESTAMP WHERE nomination_id=?").run(recommendedCeiling,recommendedCeiling,currentNomination.nominationId);
    else service.db.prepare("UPDATE nomination_decision_plans SET recommended_ceiling=?,updated_at=CURRENT_TIMESTAMP WHERE nomination_id=?").run(recommendedCeiling,currentNomination.nominationId);
    decisionPlan=service.db.prepare("SELECT recommended_ceiling recommendedCeiling,committed_ceiling committedCeiling,adjustment_reason adjustmentReason,created_at createdAt,updated_at updatedAt FROM nomination_decision_plans WHERE nomination_id=?").get(currentNomination.nominationId);
  }
  const discipline=(service.db.prepare("SELECT COUNT(*) count,COALESCE(SUM(actual_price-committed_ceiling),0) dollarsAbovePlan FROM discipline_overrides WHERE draft_id=?").get(DRAFT_ID) as any)??{count:0,dollarsAbovePlan:0};
  return {draft:{...draft,recoveryIssues:service.recoveryAudit(DRAFT_ID)},players:boardPlayers,teams:teams.map(({profile,...team})=>team),renegades:renegades?(({profile,...team})=>team)(renegades):null,roster,teamRosters,nominationOrder:{teams:nominationOrder,nextTeamId:nextNominatorTeamId},currentNomination:currentNomination?{...currentNomination,draftImpact:impactByPlayerId.get(currentNomination.playerId)??null,championshipDecision,decisionPlan}:null,leaderboard,recentSales,strategy,market:{...market,globalMultiplier:Number(market.globalMultiplier.toFixed(3))},upcomingTargets:targets,whatChanged:latestDecisionChange(service),discipline,sheetSync:sheetSyncStatus(service.db,DRAFT_ID),researchStatus:{summaryRefreshNeeded:pendingSummaryPlayers.size>0,pendingPlayerCount:pendingSummaryPlayers.size,pendingTakeawayCount:pendingSummaryTakeaways,pendingSourceCount:pendingSummarySources.size,lastSummaryGeneratedAt:summaryGeneratedAt},localSaved:true};
}

export const draftRuntime={draftId:DRAFT_ID,root:ROOT};

export function resetDraftRoom(options:{preservePreferences:boolean}){
  const service=getDraftService();
  const strategy=(service.db.prepare("SELECT strategy_json strategyJson FROM draft_strategy WHERE draft_id=?").get(DRAFT_ID) as {strategyJson:string}|undefined)?.strategyJson;
  const preferences=service.db.prepare("SELECT player_id playerId,preference,premium,note FROM player_preferences WHERE draft_id=?").all(DRAFT_ID) as {playerId:string;preference:string;premium:number;note:string}[];
  const analysisOverrides=service.db.prepare("SELECT player_id playerId,override_value overrideValue FROM fantasy_analysis_overrides WHERE draft_id=?").all(DRAFT_ID) as {playerId:string;overrideValue:string}[];
  const analysisTagOverrides=service.db.prepare("SELECT player_id playerId,tag,enabled FROM fantasy_analysis_tag_overrides WHERE draft_id=?").all(DRAFT_ID) as {playerId:string;tag:string;enabled:number}[];
  service.db.pragma("wal_checkpoint(TRUNCATE)");
  service.db.close();globalThis.__renegadeDraftService=undefined;decisionCache=null;
  const backupDirectory=join(DATA_DIR,"backups");mkdirSync(backupDirectory,{recursive:true});
  const stamp=new Date().toISOString().replaceAll(":","-").replaceAll(".","-");
  const backupPath=join(backupDirectory,`renegade-draft-room-${stamp}.sqlite`);
  if(existsSync(DATABASE_PATH))renameSync(DATABASE_PATH,backupPath);
  for(const suffix of ["-wal","-shm"]){const path=`${DATABASE_PATH}${suffix}`;if(existsSync(path))rmSync(path);}
  const fresh=getDraftService();
  if(options.preservePreferences){
    if(strategy)fresh.db.prepare("UPDATE draft_strategy SET strategy_json=?,updated_at=CURRENT_TIMESTAMP WHERE draft_id=?").run(strategy,DRAFT_ID);
    const insert=fresh.db.prepare("INSERT INTO player_preferences(draft_id,player_id,preference,premium,note,updated_at) VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)");
    fresh.db.transaction(()=>{for(const row of preferences)insert.run(DRAFT_ID,row.playerId,row.preference,row.premium,row.note);})();
    const insertAnalysisOverride=fresh.db.prepare("INSERT INTO fantasy_analysis_overrides(draft_id,player_id,override_value,updated_at) VALUES(?,?,?,CURRENT_TIMESTAMP)");
    fresh.db.transaction(()=>{for(const row of analysisOverrides)insertAnalysisOverride.run(DRAFT_ID,row.playerId,row.overrideValue);})();
    const insertTagOverride=fresh.db.prepare("INSERT INTO fantasy_analysis_tag_overrides(draft_id,player_id,tag,enabled,updated_at) VALUES(?,?,?,?,CURRENT_TIMESTAMP)");
    fresh.db.transaction(()=>{for(const row of analysisTagOverrides)insertTagOverride.run(DRAFT_ID,row.playerId,row.tag,row.enabled);})();
  }
  return {backupPath};
}

const actionSchema=z.discriminatedUnion("type",[
  z.object({type:z.literal("start")}),z.object({type:z.literal("nominate"),playerId:z.string().min(1),nominatedByTeamId:z.string().optional()}),z.object({type:z.literal("cancelNomination")}),z.object({type:z.literal("sale"),winnerTeamId:z.string().min(1),price:z.number().int().positive(),ceilingOverrideReason:z.string().max(300).optional()}),z.object({type:z.literal("voidSale"),saleId:z.string().min(1)}),z.object({type:z.literal("reassignRosterSlot"),teamId:z.string().min(1),playerId:z.string().min(1),targetSlotId:z.string().min(1)})
  ,z.object({type:z.literal("updateStrategy"),strategy:z.object({buildStyle:z.enum(["balanced","stars_and_scrubs","value_first"]),riskTolerance:z.enum(["conservative","balanced","aggressive"]),byeWeekMode:z.enum(["ignore","soft","strict"]),maxSameBye:z.number().int().min(1).max(6),targetPremium:z.number().int().min(0).max(20),situations:z.array(z.string().max(80)).max(12),teamPreferences:z.array(z.object({team:z.string().min(2).max(3),position:z.enum(["ALL","QB","RB","WR","TE","K","DEF"]),preference:z.enum(["prefer","avoid"]),adjustment:z.number().int().min(1).max(5),note:z.string().max(120)})).max(24),notes:z.string().max(1000)})})
  ,z.object({type:z.literal("playerPreference"),playerId:z.string().min(1),preference:z.enum(["target","avoid","neutral"]),premium:z.number().int().min(-50).max(50).default(0),note:z.string().max(300).default("")})
  ,z.object({type:z.literal("fantasyAnalysisOverride"),playerId:z.string().min(1),override:z.enum(["auto","target","avoid","off"])})
  ,z.object({type:z.literal("fantasyAnalysisTagOverride"),playerId:z.string().min(1),tag:z.enum(["sleeper","breakout","value","bust"]),override:z.enum(["auto","on","off"])})
  ,z.object({type:z.literal("fantasyAnalysisTagsReset"),playerId:z.string().min(1)})
  ,z.object({type:z.literal("updateNominationOrder"),teamIds:z.array(z.string().min(1)).min(2).max(20)})
  ,z.object({type:z.literal("changeNominationOwner"),nominatedByTeamId:z.string().min(1)})
  ,z.object({type:z.literal("commitCeiling"),nominationId:z.string().min(1),ceiling:z.number().int().positive(),reason:z.string().max(300).optional()})
]);

export function applyDraftAction(raw:unknown){
  const action=actionSchema.parse(raw),service=getDraftService();
  const draft=service.db.prepare("SELECT state_version FROM drafts WHERE id=?").get(DRAFT_ID) as {state_version:number};
  const command={draftId:DRAFT_ID,expectedVersion:draft.state_version,idempotencyKey:randomUUID(),occurredAt:new Date().toISOString()};
  if(action.type==="start")service.startDraft(command);
  if(action.type==="nominate")service.openNomination({...command,playerId:action.playerId,...(action.nominatedByTeamId?{nominatedByTeamId:action.nominatedByTeamId}:{})});
  if(action.type==="cancelNomination")service.cancelNomination(command);
  if(action.type==="changeNominationOwner")service.changeNominationOwner({...command,nominatedByTeamId:action.nominatedByTeamId});
  if(action.type==="sale")service.recordSale({...command,winnerTeamId:action.winnerTeamId,price:action.price,...(action.ceilingOverrideReason?{ceilingOverrideReason:action.ceilingOverrideReason}:{})});
  if(action.type==="voidSale")service.voidSale({...command,saleId:action.saleId});
  if(action.type==="reassignRosterSlot")service.reassignRosterSlot({...command,teamId:action.teamId,playerId:action.playerId,targetSlotId:action.targetSlotId});
  if(action.type==="updateStrategy")service.db.prepare("INSERT INTO draft_strategy(draft_id,strategy_json,updated_at) VALUES(?,?,?) ON CONFLICT(draft_id) DO UPDATE SET strategy_json=excluded.strategy_json,updated_at=excluded.updated_at").run(DRAFT_ID,JSON.stringify(action.strategy),command.occurredAt);
  if(action.type==="playerPreference"){
    if(action.preference==="neutral")service.db.prepare("DELETE FROM player_preferences WHERE draft_id=? AND player_id=?").run(DRAFT_ID,action.playerId);
    else service.db.prepare("INSERT INTO player_preferences(draft_id,player_id,preference,premium,note,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(draft_id,player_id) DO UPDATE SET preference=excluded.preference,premium=excluded.premium,note=excluded.note,updated_at=excluded.updated_at").run(DRAFT_ID,action.playerId,action.preference,action.premium,action.note,command.occurredAt);
  }
  if(action.type==="fantasyAnalysisOverride"){
    if(action.override==="auto")service.db.prepare("DELETE FROM fantasy_analysis_overrides WHERE draft_id=? AND player_id=?").run(DRAFT_ID,action.playerId);
    else service.db.prepare("INSERT INTO fantasy_analysis_overrides(draft_id,player_id,override_value,updated_at) VALUES(?,?,?,?) ON CONFLICT(draft_id,player_id) DO UPDATE SET override_value=excluded.override_value,updated_at=excluded.updated_at").run(DRAFT_ID,action.playerId,action.override,command.occurredAt);
  }
  if(action.type==="fantasyAnalysisTagOverride"){
    if(action.override==="auto")service.db.prepare("DELETE FROM fantasy_analysis_tag_overrides WHERE draft_id=? AND player_id=? AND tag=?").run(DRAFT_ID,action.playerId,action.tag);
    else service.db.prepare("INSERT INTO fantasy_analysis_tag_overrides(draft_id,player_id,tag,enabled,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(draft_id,player_id,tag) DO UPDATE SET enabled=excluded.enabled,updated_at=excluded.updated_at").run(DRAFT_ID,action.playerId,action.tag,action.override==="on"?1:0,command.occurredAt);
  }
  if(action.type==="fantasyAnalysisTagsReset")service.db.prepare("DELETE FROM fantasy_analysis_tag_overrides WHERE draft_id=? AND player_id=?").run(DRAFT_ID,action.playerId);
  if(action.type==="updateNominationOrder"){
    const draftTeamIds=(service.db.prepare("SELECT id FROM teams WHERE draft_id=?").all(DRAFT_ID) as {id:string}[]).map(row=>row.id);
    if(action.teamIds.length!==draftTeamIds.length||new Set(action.teamIds).size!==draftTeamIds.length||action.teamIds.some(id=>!draftTeamIds.includes(id)))throw new DomainError("INVALID_NOMINATION_ORDER","Nomination order must include every owner exactly once");
    const update=service.db.prepare("UPDATE draft_nomination_order SET ordinal=?,updated_at=? WHERE draft_id=? AND team_id=?");service.db.transaction(()=>{service.db.prepare("UPDATE draft_nomination_order SET ordinal=ordinal+100 WHERE draft_id=?").run(DRAFT_ID);action.teamIds.forEach((teamId,index)=>update.run(index+1,command.occurredAt,DRAFT_ID,teamId));})();
  }
  if(action.type==="commitCeiling"){
    const plan=service.db.prepare(`SELECT plan.recommended_ceiling recommendedCeiling,t.id renegadesId,s.remaining_budget remainingBudget,s.open_slot_count openSlots,d.minimum_bid minimumBid FROM nomination_decision_plans plan JOIN nominations n ON n.id=plan.nomination_id JOIN teams t ON t.draft_id=plan.draft_id AND t.display_name='Rodman Renegades' JOIN team_draft_state s ON s.team_id=t.id JOIN drafts d ON d.id=plan.draft_id WHERE plan.nomination_id=? AND plan.draft_id=? AND n.status='open'`).get(action.nominationId,DRAFT_ID) as any;
    if(!plan)throw new DomainError("DECISION_PLAN_NOT_FOUND","The active nomination plan was not found");
    const maximum=plan.remainingBudget-(plan.openSlots-1)*plan.minimumBid;
    if(action.ceiling>maximum)throw new DomainError("CEILING_ABOVE_LEGAL_MAX",`The ceiling cannot exceed the $${maximum} legal maximum bid`);
    service.db.prepare("UPDATE nomination_decision_plans SET committed_ceiling=?,adjustment_reason=?,updated_at=? WHERE nomination_id=? AND draft_id=?").run(action.ceiling,action.reason?.trim()||null,command.occurredAt,action.nominationId,DRAFT_ID);
  }
  const view=readDraftRoom();recordDecisionSnapshot(service,view,action.type,command.idempotencyKey);return readDraftRoom();
}

export function toApiError(error:unknown){
  if(error instanceof z.ZodError)return {status:400,body:{error:"INVALID_INPUT",message:"Check the entered values and try again."}};
  if(error instanceof DomainError)return {status:409,body:{error:error.code,message:error.message}};
  console.error(error);return {status:500,body:{error:"UNEXPECTED_ERROR",message:"The action was not saved. Your prior draft state is unchanged."}};
}
