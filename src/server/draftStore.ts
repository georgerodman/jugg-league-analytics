import { existsSync, mkdirSync, readFileSync, renameSync, rmSync } from "node:fs";
import { join, resolve } from "node:path";
import { randomUUID } from "node:crypto";
import { z } from "zod";
import { DraftService, DomainError } from "../domain/DraftService";
import { initializeFromArtifacts } from "../domain/importDraftArtifacts";
import { sheetSyncStatus } from "./googleSheetsSync";
import { liveLeaderboard, nominationDecision, type DecisionPlayer, type DecisionTeam, type Position } from "../domain/liveDecisionEngine";

const ROOT=process.cwd(), DRAFT_ID="jugg-2026", DATA_DIR=join(ROOT,".local");
const DATABASE_PATH=process.env.RENEGADE_DB_PATH??join(DATA_DIR,"renegade-draft-room.sqlite");

type OwnerProfile={owner:string;evidence_strength:string;construction_style:string;positions:Record<string,{signal:string;direction_consistency:number}>;repeat_players:{internal_player_id:string;player_name:string;times_drafted:number}[]};
type TeamPreference={team:string;position:"ALL"|"QB"|"RB"|"WR"|"TE"|"K"|"DEF";preference:"prefer"|"avoid";adjustment:number;note:string};
type Strategy={buildStyle:"balanced"|"stars_and_scrubs"|"value_first";riskTolerance:"conservative"|"balanced"|"aggressive";byeWeekMode:"ignore"|"soft"|"strict";maxSameBye:number;targetPremium:number;situations:string[];teamPreferences:TeamPreference[];notes:string};
const DEFAULT_STRATEGY:Strategy={buildStyle:"balanced",riskTolerance:"balanced",byeWeekMode:"soft",maxSameBye:2,targetPremium:3,situations:[],teamPreferences:[],notes:""};
declare global { var __renegadeDraftService:DraftService|undefined; }

function latest(path:string):any{return JSON.parse(readFileSync(resolve(ROOT,path),"utf8"));}
function rounded(value:number|null|undefined):number|null{return value==null?null:Math.round(value);}
function parseJson<T>(value:string|null,fallback:T):T{try{return value?JSON.parse(value) as T:fallback;}catch{return fallback;}}

export function getDraftService():DraftService{
  // Next.js keeps this singleton across hot reloads. If the domain service gains
  // a new command, discard an older in-memory instance so its prototype cannot
  // lag behind the newly loaded server code.
  const cachedService=globalThis.__renegadeDraftService;
  const needsCurrentMigrations=cachedService&&!cachedService.db.prepare("SELECT 1 FROM sqlite_master WHERE type='table' AND name='draft_nomination_order'").get();
  if(cachedService&&(typeof cachedService.reassignRosterSlot!=="function"||needsCurrentMigrations)){
    cachedService.db.close();
    globalThis.__renegadeDraftService=undefined;
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
    const espnPointer=latest("data/processed/espn_salary_cap_values/2026/latest.json"),espn=latest(espnPointer.artifact!);
    const byeByPlayer=new Map((espn.values as any[]).map(row=>[row.internal_player_id,row.bye_week]));
    const byeByTeam=new Map((espn.values as any[]).map(row=>[row.nfl_team,row.bye_week]));
    const update=service.db.prepare("UPDATE draft_player_pool SET adp_espn=?,adp_yahoo=?,bye_week=? WHERE draft_id=? AND player_id=?");
    service.db.transaction(()=>{for(const row of board.players as any[])update.run(row.adp_espn,row.adp_yahoo,byeByPlayer.get(row.internal_player_id)??byeByTeam.get(row.nfl_team)??null,DRAFT_ID,row.internal_player_id);})();
    service.db.prepare("INSERT OR IGNORE INTO draft_strategy(draft_id,strategy_json) VALUES(?,?)").run(DRAFT_ID,JSON.stringify(DEFAULT_STRATEGY));
  }
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

export function readDraftRoom(){
  const service=getDraftService();
  const draft=service.db.prepare("SELECT id,status,state_version stateVersion FROM drafts WHERE id=?").get(DRAFT_ID) as any;
  const storedStrategy=parseJson<Partial<Strategy>>((service.db.prepare("SELECT strategy_json strategyJson FROM draft_strategy WHERE draft_id=?").get(DRAFT_ID) as any)?.strategyJson,DEFAULT_STRATEGY);
  const strategy:Strategy={...DEFAULT_STRATEGY,...storedStrategy,teamPreferences:storedStrategy.teamPreferences??[],situations:storedStrategy.situations??[]};
  const market=marketContext(service);
  const productionPointer=latest("data/processed/production_value_model/latest.json"),decisionBoard=latest(productionPointer.decision_board_json!);
  const projectedById=new Map((decisionBoard.players as any[]).map(row=>[row.internal_player_id,Number(row.projected_points??0)]));
  const productionById=new Map((decisionBoard.players as any[]).map(row=>[row.internal_player_id,row]));
  const renegadeId=(service.db.prepare("SELECT id FROM teams WHERE draft_id=? AND display_name='Rodman Renegades'").get(DRAFT_ID) as any)?.id;
  const byeCounts=new Map<number,number>();
  for(const row of service.db.prepare(`SELECT pool.bye_week byeWeek FROM roster_slots rs JOIN draft_player_pool pool ON pool.draft_id=? AND pool.player_id=rs.player_id WHERE rs.team_id=? AND rs.player_id IS NOT NULL`).all(DRAFT_ID,renegadeId) as {byeWeek:number|null}[])if(row.byeWeek)byeCounts.set(row.byeWeek,(byeCounts.get(row.byeWeek)??0)+1);
  const rawPlayers=service.db.prepare(`SELECT p.id,p.display_name name,p.position,p.nfl_team nflTeam,pool.status,pool.expected_price expectedPrice,pool.price_low priceLow,pool.price_high priceHigh,pool.production_value productionValue,pool.expected_surplus edge,pool.draft_probability draftProbability,pool.risk_flags_json riskFlags,pool.adp_espn adpEspn,pool.adp_yahoo adpYahoo,pool.bye_week byeWeek,pref.preference,pref.premium preferencePremium,pref.note preferenceNote,s.price salePrice,winner.display_name draftedBy FROM draft_player_pool pool JOIN players p ON p.id=pool.player_id LEFT JOIN player_preferences pref ON pref.draft_id=pool.draft_id AND pref.player_id=pool.player_id LEFT JOIN sales s ON s.draft_id=pool.draft_id AND s.player_id=pool.player_id AND s.voided_event_id IS NULL LEFT JOIN teams winner ON winner.id=s.winner_team_id WHERE pool.draft_id=? ORDER BY pool.expected_price DESC,p.display_name`).all(DRAFT_ID) as any[];
  const players=rawPlayers.map(row=>{
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
    const strategyValue=rounded(Math.max(0,(row.productionValue??0)+adjustment));
    return {...row,projectedPoints:projectedById.get(row.id)??0,expectedPrice:rounded(row.expectedPrice),priceLow:rounded(row.priceLow),priceHigh:rounded(row.priceHigh),liveExpectedPrice:liveExpected,livePriceLow:row.priceLow==null?null:rounded(row.priceLow*multiplier),livePriceHigh:row.priceHigh==null?null:rounded(row.priceHigh*multiplier),marketMultiplier:Number(multiplier.toFixed(3)),marketAdp:rounded(([row.adpEspn,row.adpYahoo].filter(Number.isFinite) as number[]).reduce((sum,value)=>sum+value,0)/([row.adpEspn,row.adpYahoo].filter(Number.isFinite).length||1))||null,productionValue:rounded(row.productionValue),edge:rounded(row.edge),liveEdge:strategyValue==null||liveExpected==null?null:strategyValue-liveExpected,strategyValue,strategyReasons:reasons,riskFlags};
  });
  const teams=(service.db.prepare(`SELECT t.id,t.display_name name,o.display_name owner,s.remaining_budget remainingBudget,s.open_slot_count openSlots,s.rostered_player_count rosteredCount,d.minimum_bid minimumBid,o.profile_json profileJson FROM teams t JOIN owners o ON o.id=t.owner_id JOIN team_draft_state s ON s.team_id=t.id JOIN drafts d ON d.id=t.draft_id WHERE t.draft_id=? ORDER BY CASE WHEN t.display_name='Rodman Renegades' THEN 0 ELSE 1 END,s.remaining_budget DESC`).all(DRAFT_ID) as any[]).map(row=>({...row,maxBid:row.remainingBudget-(row.openSlots-1)*row.minimumBid,profile:parseJson<OwnerProfile|null>(row.profileJson,null),profileJson:undefined}));
  const nominationOrderCount=(service.db.prepare("SELECT COUNT(*) count FROM draft_nomination_order WHERE draft_id=?").get(DRAFT_ID) as {count:number}).count;
  if(nominationOrderCount===0){const alphabetical=[...teams].sort((a,b)=>a.owner.localeCompare(b.owner,undefined,{sensitivity:"base"}));const insert=service.db.prepare("INSERT INTO draft_nomination_order(draft_id,team_id,ordinal) VALUES(?,?,?)");service.db.transaction(()=>alphabetical.forEach((team,index)=>insert.run(DRAFT_ID,team.id,index+1)))();}
  const nominationOrder=service.db.prepare(`WITH active_completions AS (SELECT c.team_id,c.completed_at,e.sequence,ROW_NUMBER() OVER (ORDER BY e.sequence) waiverPriority FROM team_draft_completions c JOIN draft_events e ON e.id=c.completed_event_id WHERE c.draft_id=? AND c.voided_event_id IS NULL) SELECT no.team_id teamId,no.ordinal,t.display_name team,o.display_name owner,s.open_slot_count openSlots,ac.completed_at completedAt,ac.waiverPriority FROM draft_nomination_order no JOIN teams t ON t.id=no.team_id JOIN owners o ON o.id=t.owner_id JOIN team_draft_state s ON s.team_id=t.id LEFT JOIN active_completions ac ON ac.team_id=t.id WHERE no.draft_id=? ORDER BY no.ordinal`).all(DRAFT_ID,DRAFT_ID) as any[];
  const lastNominator=(service.db.prepare(`SELECT n.nominated_by_team_id teamId FROM nominations n JOIN draft_events e ON e.id=n.opened_event_id WHERE n.draft_id=? AND n.nominated_by_team_id IS NOT NULL ORDER BY e.sequence DESC LIMIT 1`).get(DRAFT_ID) as {teamId:string}|undefined)?.teamId;
  const lastIndex=nominationOrder.findIndex(row=>row.teamId===lastNominator);let nextNominatorTeamId:string|null=null;
  for(let offset=1;offset<=nominationOrder.length;offset++){const candidate=nominationOrder[(lastIndex+offset+nominationOrder.length)%nominationOrder.length];if(candidate&&candidate.openSlots>0){nextNominatorTeamId=candidate.teamId;break;}}
  const nomination=service.db.prepare(`SELECT n.id,p.id playerId,p.display_name name,p.position,p.nfl_team nflTeam,pool.expected_price expectedPrice,pool.price_low priceLow,pool.price_high priceHigh,pool.production_value productionValue,pool.expected_surplus edge,pool.risk_flags_json riskFlags,t.id nominatorTeamId,o.display_name nominator FROM nominations n JOIN players p ON p.id=n.player_id JOIN draft_player_pool pool ON pool.draft_id=n.draft_id AND pool.player_id=n.player_id LEFT JOIN teams t ON t.id=n.nominated_by_team_id LEFT JOIN owners o ON o.id=t.owner_id WHERE n.draft_id=? AND n.status='open'`).get(DRAFT_ID) as any;
  let currentNomination:any=null;
  if(nomination){
    const nominatorTeam=teams.find(team=>team.id===nomination.nominatorTeamId);
    const enriched=players.find(player=>player.id===nomination.playerId)!;
    const competition=teams.filter(team=>team.name!=="Rodman Renegades"&&team.maxBid>=Math.max(1,enriched.liveExpectedPrice??enriched.expectedPrice??1)).slice(0,4).map(team=>({id:team.id,name:team.owner,maxBid:team.maxBid,signal:ownerSignal(team.profile,nomination.position,nomination.playerId)}));
    const nominatedPrice=Math.max(1,enriched.liveExpectedPrice??enriched.expectedPrice??1);
    const nominatedPoints=Math.max(1,enriched.projectedPoints??1);
    const comparableScore=(player:any)=>{
      const candidatePrice=Math.max(1,player.liveExpectedPrice??player.expectedPrice??1);
      const candidatePoints=Math.max(1,player.projectedPoints??1);
      return Math.abs(Math.log(candidatePrice/nominatedPrice))+.65*Math.abs(Math.log(candidatePoints/nominatedPoints));
    };
    const alternatives=players
      .filter(player=>player.status==="available"&&player.id!==nomination.playerId&&player.position===nomination.position)
      .sort((a,b)=>comparableScore(a)-comparableScore(b)||(b.liveExpectedPrice??0)-(a.liveExpectedPrice??0))
      .slice(0,3);
    currentNomination={...enriched,playerId:nomination.playerId,nominator:nomination.nominator,ownerSignal:ownerSignal(nominatorTeam?.profile??null,nomination.position,nomination.playerId),competition,alternatives};
  }
  const recentSales=service.db.prepare(`SELECT s.id,ROW_NUMBER() OVER (ORDER BY e.sequence) pick,p.display_name player,t.display_name team,s.price,s.recorded_at recordedAt FROM sales s JOIN draft_events e ON e.id=s.recorded_event_id JOIN players p ON p.id=s.player_id JOIN teams t ON t.id=s.winner_team_id WHERE s.draft_id=? AND s.voided_event_id IS NULL ORDER BY e.sequence DESC`).all(DRAFT_ID);
  const renegades=teams.find(team=>team.name==="Rodman Renegades")??teams[0];
  const rawRosters=service.db.prepare(`SELECT rs.id slotId,rs.team_id teamId,rs.slot_type slotType,rs.ordinal,rs.eligible_positions_json eligiblePositionsJson,p.id playerId,p.display_name player,p.position,pool.bye_week byeWeek,s.price pricePaid FROM roster_slots rs JOIN teams t ON t.id=rs.team_id LEFT JOIN players p ON p.id=rs.player_id LEFT JOIN draft_player_pool pool ON pool.draft_id=? AND pool.player_id=rs.player_id LEFT JOIN sales s ON s.id=rs.filled_sale_id AND s.voided_event_id IS NULL WHERE t.draft_id=? ORDER BY t.display_name,CASE rs.slot_type WHEN 'QB' THEN 1 WHEN 'WR' THEN 2 WHEN 'RB' THEN 3 WHEN 'TE' THEN 4 WHEN 'WR_RB' THEN 5 WHEN 'WR_RB_TE' THEN 6 WHEN 'DEF' THEN 7 WHEN 'K' THEN 8 ELSE 9 END,rs.ordinal`).all(DRAFT_ID,DRAFT_ID) as any[];
  const strengthThresholds:Record<string,[number,number,number]>={QB:[3,7,10],RB:[5,12,24],WR:[5,15,30],TE:[3,7,12],K:[3,7,10],DEF:[3,7,10]};
  const enrichedRosters=rawRosters.map(row=>{const production=productionById.get(row.playerId) as any;const rank=Number(production?.position_rank)||null,thresholds=strengthThresholds[row.position]??[3,7,10];const strength=!rank?null:rank<=thresholds[0]?"Elite":rank<=thresholds[1]?"Strong":rank<=thresholds[2]?"Starter":"Depth";return {...row,eligiblePositions:parseJson<Position[]>(row.eligiblePositionsJson,[]),eligiblePositionsJson:undefined,positionRank:rank,pointsAboveReplacement:production?.points_above_replacement==null?null:Number(production.points_above_replacement),strength};});
  const teamRosters=Object.fromEntries(teams.map(team=>[team.id,enrichedRosters.filter(row=>row.teamId===team.id)]));
  const roster=renegades?teamRosters[renegades.id]??[]:[];
  const decisionPlayers=new Map(players.map(player=>[player.id,{id:player.id,name:player.name,position:player.position as Position,projectedPoints:player.projectedPoints,
    expectedPrice:Math.max(1,player.liveExpectedPrice??player.expectedPrice??1),priceLow:Math.max(1,player.livePriceLow??player.priceLow??1),priceHigh:Math.max(1,player.livePriceHigh??player.priceHigh??1)} satisfies DecisionPlayer]));
  const rosterRows=service.db.prepare(`SELECT rs.team_id teamId,rs.player_id playerId FROM roster_slots rs JOIN teams t ON t.id=rs.team_id WHERE t.draft_id=? AND rs.player_id IS NOT NULL`).all(DRAFT_ID) as {teamId:string;playerId:string}[];
  const decisionTeams:DecisionTeam[]=teams.map(team=>({id:team.id,name:team.name,owner:team.owner,remainingBudget:team.remainingBudget,openSlots:team.openSlots,
    roster:rosterRows.filter(row=>row.teamId===team.id).map(row=>decisionPlayers.get(row.playerId)).filter((player):player is DecisionPlayer=>Boolean(player))}));
  const availableDecisionPlayers=players.filter(player=>player.status==="available"||player.status==="nominated").map(player=>decisionPlayers.get(player.id)).filter((player):player is DecisionPlayer=>Boolean(player));
  const leaderboard=liveLeaderboard(decisionTeams,availableDecisionPlayers);
  const championshipDecision=currentNomination&&renegades?nominationDecision(decisionTeams,renegades.id,availableDecisionPlayers,currentNomination.playerId,renegades.maxBid):null;
  return {draft:{...draft,recoveryIssues:service.recoveryAudit(DRAFT_ID)},players,teams:teams.map(({profile,...team})=>team),renegades:renegades?(({profile,...team})=>team)(renegades):null,roster,teamRosters,nominationOrder:{teams:nominationOrder,nextTeamId:nextNominatorTeamId},currentNomination:currentNomination?{...currentNomination,championshipDecision}:null,leaderboard,recentSales,strategy,market:{...market,globalMultiplier:Number(market.globalMultiplier.toFixed(3))},sheetSync:sheetSyncStatus(service.db,DRAFT_ID),localSaved:true};
}

export const draftRuntime={draftId:DRAFT_ID,root:ROOT};

export function resetDraftRoom(options:{preservePreferences:boolean}){
  const service=getDraftService();
  const strategy=(service.db.prepare("SELECT strategy_json strategyJson FROM draft_strategy WHERE draft_id=?").get(DRAFT_ID) as {strategyJson:string}|undefined)?.strategyJson;
  const preferences=service.db.prepare("SELECT player_id playerId,preference,premium,note FROM player_preferences WHERE draft_id=?").all(DRAFT_ID) as {playerId:string;preference:string;premium:number;note:string}[];
  service.db.pragma("wal_checkpoint(TRUNCATE)");
  service.db.close();globalThis.__renegadeDraftService=undefined;
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
  }
  return {backupPath};
}

const actionSchema=z.discriminatedUnion("type",[
  z.object({type:z.literal("start")}),z.object({type:z.literal("nominate"),playerId:z.string().min(1),nominatedByTeamId:z.string().optional()}),z.object({type:z.literal("cancelNomination")}),z.object({type:z.literal("sale"),winnerTeamId:z.string().min(1),price:z.number().int().positive()}),z.object({type:z.literal("voidSale"),saleId:z.string().min(1)}),z.object({type:z.literal("reassignRosterSlot"),teamId:z.string().min(1),playerId:z.string().min(1),targetSlotId:z.string().min(1)})
  ,z.object({type:z.literal("updateStrategy"),strategy:z.object({buildStyle:z.enum(["balanced","stars_and_scrubs","value_first"]),riskTolerance:z.enum(["conservative","balanced","aggressive"]),byeWeekMode:z.enum(["ignore","soft","strict"]),maxSameBye:z.number().int().min(1).max(6),targetPremium:z.number().int().min(0).max(20),situations:z.array(z.string().max(80)).max(12),teamPreferences:z.array(z.object({team:z.string().min(2).max(3),position:z.enum(["ALL","QB","RB","WR","TE","K","DEF"]),preference:z.enum(["prefer","avoid"]),adjustment:z.number().int().min(1).max(5),note:z.string().max(120)})).max(24),notes:z.string().max(1000)})})
  ,z.object({type:z.literal("playerPreference"),playerId:z.string().min(1),preference:z.enum(["target","avoid","neutral"]),premium:z.number().int().min(-50).max(50).default(0),note:z.string().max(300).default("")})
  ,z.object({type:z.literal("updateNominationOrder"),teamIds:z.array(z.string().min(1)).min(2).max(20)})
]);

export function applyDraftAction(raw:unknown){
  const action=actionSchema.parse(raw),service=getDraftService();
  const draft=service.db.prepare("SELECT state_version FROM drafts WHERE id=?").get(DRAFT_ID) as {state_version:number};
  const command={draftId:DRAFT_ID,expectedVersion:draft.state_version,idempotencyKey:randomUUID(),occurredAt:new Date().toISOString()};
  if(action.type==="start")service.startDraft(command);
  if(action.type==="nominate")service.openNomination({...command,playerId:action.playerId,...(action.nominatedByTeamId?{nominatedByTeamId:action.nominatedByTeamId}:{})});
  if(action.type==="cancelNomination")service.cancelNomination(command);
  if(action.type==="sale")service.recordSale({...command,winnerTeamId:action.winnerTeamId,price:action.price});
  if(action.type==="voidSale")service.voidSale({...command,saleId:action.saleId});
  if(action.type==="reassignRosterSlot")service.reassignRosterSlot({...command,teamId:action.teamId,playerId:action.playerId,targetSlotId:action.targetSlotId});
  if(action.type==="updateStrategy")service.db.prepare("INSERT INTO draft_strategy(draft_id,strategy_json,updated_at) VALUES(?,?,?) ON CONFLICT(draft_id) DO UPDATE SET strategy_json=excluded.strategy_json,updated_at=excluded.updated_at").run(DRAFT_ID,JSON.stringify(action.strategy),command.occurredAt);
  if(action.type==="playerPreference"){
    if(action.preference==="neutral")service.db.prepare("DELETE FROM player_preferences WHERE draft_id=? AND player_id=?").run(DRAFT_ID,action.playerId);
    else service.db.prepare("INSERT INTO player_preferences(draft_id,player_id,preference,premium,note,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(draft_id,player_id) DO UPDATE SET preference=excluded.preference,premium=excluded.premium,note=excluded.note,updated_at=excluded.updated_at").run(DRAFT_ID,action.playerId,action.preference,action.premium,action.note,command.occurredAt);
  }
  if(action.type==="updateNominationOrder"){
    const draftTeamIds=(service.db.prepare("SELECT id FROM teams WHERE draft_id=?").all(DRAFT_ID) as {id:string}[]).map(row=>row.id);
    if(action.teamIds.length!==draftTeamIds.length||new Set(action.teamIds).size!==draftTeamIds.length||action.teamIds.some(id=>!draftTeamIds.includes(id)))throw new DomainError("INVALID_NOMINATION_ORDER","Nomination order must include every owner exactly once");
    const update=service.db.prepare("UPDATE draft_nomination_order SET ordinal=?,updated_at=? WHERE draft_id=? AND team_id=?");service.db.transaction(()=>{service.db.prepare("UPDATE draft_nomination_order SET ordinal=ordinal+100 WHERE draft_id=?").run(DRAFT_ID);action.teamIds.forEach((teamId,index)=>update.run(index+1,command.occurredAt,DRAFT_ID,teamId));})();
  }
  return readDraftRoom();
}

export function toApiError(error:unknown){
  if(error instanceof z.ZodError)return {status:400,body:{error:"INVALID_INPUT",message:"Check the entered values and try again."}};
  if(error instanceof DomainError)return {status:409,body:{error:error.code,message:error.message}};
  console.error(error);return {status:500,body:{error:"UNEXPECTED_ERROR",message:"The action was not saved. Your prior draft state is unchanged."}};
}
