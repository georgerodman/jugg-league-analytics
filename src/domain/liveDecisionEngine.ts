export type Position="QB"|"RB"|"WR"|"TE"|"K"|"DEF";

export type DecisionPlayer={
  id:string;name:string;position:Position;projectedPoints:number;
  expectedPrice:number;priceLow:number;priceHigh:number;
  productionTier?:number;auctionTier?:number;pointsAboveReplacement?:number;replacementPoints?:number;
  strategyValue?:number;strategyAdjustment?:number;preference?:"target"|"avoid"|null;strategyReasons?:string[];
};
export type UpcomingTarget={rank:number;playerId:string;name:string;position:Position;role:string;targetPrice:number;walkawayCeiling:number;expectedEquityDelta:number;scenarioSupport:number;productionTier:number|null;tierRemaining:number;tierDropPoints:number;replacementPlayer:string|null;replacementPrice:number|null;why:string;conditionalPlan:string;strategyReasons:string[]};
export type DraftImpact={playerId:string;price:number;band:DecisionBand;label:"Great Add"|"Good Add"|"Neutral"|"Poor Add"|"Bad Add";expectedEquityDelta:number;scenarioSupport:number;role:string;summary:string};

export type DecisionTeam={
  id:string;name:string;owner:string;remainingBudget:number;openSlots:number;
  roster:DecisionPlayer[];
};

export type DecisionBand="strong_pursue"|"lean_pursue"|"neutral"|"lean_pass"|"strong_pass";
export type RosterCompletion={players:DecisionPlayer[];remainingBudget:number;projectedLineupPoints:number};
type PriceScenario="favorable"|"expected"|"adverse";
type Objective="lineup"|"efficiency"|"ceiling";

const PRICE_SCENARIOS:PriceScenario[]=["favorable","expected","adverse"];
const OBJECTIVES:Objective[]=["lineup","efficiency","ceiling"];
const REQUIRED:Record<Position,number>={QB:1,WR:2,RB:1,TE:1,K:1,DEF:1};
const ROSTER_SIZE=14;
const EQUITY_SCALE=95;
const NOISE_FLOOR=.014;

function price(player:DecisionPlayer,scenario:PriceScenario){
  return Math.max(1,Math.round(scenario==="favorable"?player.priceLow:scenario==="adverse"?player.priceHigh:player.expectedPrice));
}

function utility(player:DecisionPlayer,scenario:PriceScenario,objective:Objective){
  const cost=price(player,scenario),points=player.projectedPoints;
  if(objective==="efficiency")return points/cost;
  if(objective==="ceiling")return points/(cost**.45);
  return points;
}

export function lineupPoints(players:DecisionPlayer[]){
  const fixed=(position:Position)=>Math.max(0,...players.filter(player=>player.position===position).map(player=>player.projectedPoints));
  const skill=players.filter(player=>["RB","WR","TE"].includes(player.position));
  let best=0;
  for(let left=0;left<skill.length;left++)for(let right=0;right<skill.length;right++){
    const leftPlayer=skill[left],rightPlayer=skill[right];
    if(!leftPlayer||!rightPlayer||left===right||!["RB","WR"].includes(leftPlayer.position))continue;
    const remaining=skill.filter((_,index)=>index!==left&&index!==right);
    const wr=remaining.filter(player=>player.position==="WR").sort((a,b)=>b.projectedPoints-a.projectedPoints);
    const rb=remaining.filter(player=>player.position==="RB").sort((a,b)=>b.projectedPoints-a.projectedPoints);
    const te=remaining.filter(player=>player.position==="TE").sort((a,b)=>b.projectedPoints-a.projectedPoints);
    const firstWr=wr[0],secondWr=wr[1],firstRb=rb[0],firstTe=te[0];
    if(firstWr&&secondWr&&firstRb&&firstTe)best=Math.max(best,firstWr.projectedPoints+secondWr.projectedPoints+firstRb.projectedPoints+firstTe.projectedPoints+leftPlayer.projectedPoints+rightPlayer.projectedPoints);
  }
  return fixed("QB")+fixed("K")+fixed("DEF")+best;
}

export function completeRoster(team:DecisionTeam,candidates:DecisionPlayer[],scenario:PriceScenario,objective:Objective):RosterCompletion|null{
  const chosen=[...team.roster],used=new Set(chosen.map(player=>player.id));
  const available=candidates.filter(player=>!used.has(player.id)).sort((a,b)=>utility(b,scenario,objective)-utility(a,scenario,objective)||price(a,scenario)-price(b,scenario)||a.name.localeCompare(b.name));let budget=team.remainingBudget;
  const affordable=(player:DecisionPlayer)=>price(player,scenario)+(ROSTER_SIZE-chosen.length-1)<=budget;
  const addBest=(positions:Set<Position>)=>{
    const selected=available.find(player=>positions.has(player.position)&&affordable(player));if(!selected)return false;
    chosen.push(selected);budget-=price(selected,scenario);available.splice(available.indexOf(selected),1);return true;
  };
  const count=(positions:Set<Position>)=>chosen.filter(player=>positions.has(player.position)).length;
  const failed=():RosterCompletion|null=>objective==="efficiency"?null:completeRoster(team,candidates,scenario,"efficiency");
  for(const [position,minimum] of Object.entries(REQUIRED) as [Position,number][]){
    while(count(new Set([position]))<minimum)if(!addBest(new Set([position])))return failed();
  }
  while(count(new Set(["WR","RB"]))<4)if(!addBest(new Set(["WR","RB"])))return failed();
  while(count(new Set(["WR","RB","TE"]))<6)if(!addBest(new Set(["WR","RB","TE"])))return failed();
  while(chosen.length<ROSTER_SIZE)if(!addBest(new Set(["QB","RB","WR","TE","K","DEF"])))return failed();
  return {players:chosen,remainingBudget:budget,projectedLineupPoints:lineupPoints(chosen)};
}

function equity(scores:Record<string,number>):Record<string,number>{
  const maximum=Math.max(...Object.values(scores));const weights=Object.fromEntries(Object.entries(scores).map(([id,score])=>[id,Math.exp((score-maximum)/EQUITY_SCALE)]));
  const total=Object.values(weights).reduce((sum,value)=>sum+value,0);
  return Object.fromEntries(Object.entries(weights).map(([id,value])=>[id,value/total]));
}

function band(deltas:number[]):DecisionBand{
  if(!deltas.length)return "neutral";
  const ordered=[...deltas].sort((a,b)=>a-b),median=ordered[Math.floor(ordered.length/2)]??0,positive=ordered.filter(value=>value>0).length/ordered.length;
  const robustLow=ordered[Math.floor(.2*(ordered.length-1))]??0,robustHigh=ordered[Math.ceil(.8*(ordered.length-1))]??0;
  const strong=Math.max(.03,2*NOISE_FLOOR),lean=Math.max(.0125,1.25*NOISE_FLOOR);
  if(median>=strong&&robustLow>0&&positive>=.8)return "strong_pursue";
  if(median>=lean&&positive>=2/3)return "lean_pursue";
  if(median<=-strong&&robustHigh<0&&positive<=.2)return "strong_pass";
  if(median<=-lean&&positive<=1/3)return "lean_pass";
  return "neutral";
}

function percentile(values:number[],fraction:number){const sorted=[...values].sort((a,b)=>a-b);return sorted[Math.round((sorted.length-1)*fraction)]??0;}

function baselineScenarioScores(teams:DecisionTeam[],available:DecisionPlayer[]){
  const result:{scenario:PriceScenario;objective:Objective;scores:Record<string,number>}[]=[];
  for(const scenario of PRICE_SCENARIOS)for(const objective of OBJECTIVES){
    const scores:Record<string,number>={};
    for(const team of teams)scores[team.id]=completeRoster(team,available,scenario,objective)?.projectedLineupPoints??lineupPoints(team.roster);
    result.push({scenario,objective,scores});
  }
  return result;
}

function median(values:number[]){const ordered=[...values].sort((a,b)=>a-b);return ordered[Math.floor(ordered.length/2)]??0;}

function rosterRole(team:DecisionTeam,position:Position){
  const count=team.roster.filter(player=>player.position===position).length;
  if(count<(REQUIRED[position]??0))return `Fill starting ${position}`;
  if(["RB","WR","TE"].includes(position)&&team.roster.filter(player=>["RB","WR","TE"].includes(player.position)).length<6)return "Build flex options";
  return `Add ${position} depth`;
}

const impactLabels:Record<DecisionBand,DraftImpact["label"]>={strong_pursue:"Great Add",lean_pursue:"Good Add",neutral:"Neutral",lean_pass:"Poor Add",strong_pass:"Bad Add"};

export function draftRoadmap(teams:DecisionTeam[],renegadesId:string,available:DecisionPlayer[],maxBid:number):{targets:UpcomingTarget[];impacts:DraftImpact[]}{
  const renegades=teams.find(team=>team.id===renegadesId);if(!renegades)return{targets:[],impacts:[]};
  const baseline=baselineScenarioScores(teams,available);
  const tierCounts=new Map<string,number>();
  for(const player of available)if(player.productionTier)tierCounts.set(`${player.position}:${player.productionTier}`,(tierCounts.get(`${player.position}:${player.productionTier}`)??0)+1);
  const evaluated=available.filter(player=>player.expectedPrice<=maxBid).map(player=>{
    const poolWithout=available.filter(row=>row.id!==player.id),deltas:number[]=[];
    const purchasePrice=Math.max(1,Math.round(player.expectedPrice));
    for(const row of baseline){
      const passEquity=equity(row.scores)[renegadesId]??0;
      const buyingTeam={...renegades,remainingBudget:renegades.remainingBudget-purchasePrice,openSlots:renegades.openSlots-1,roster:[...renegades.roster,player]};
      const completion=completeRoster(buyingTeam,poolWithout,row.scenario,row.objective);
      const buyScores={...row.scores,[renegadesId]:completion?.projectedLineupPoints??lineupPoints(buyingTeam.roster)};
      deltas.push((equity(buyScores)[renegadesId]??0)-passEquity);
    }
    const productionTier=player.productionTier??null,tierRemaining=productionTier?tierCounts.get(`${player.position}:${productionTier}`)??0:0;
    const nextTierPlayer=productionTier?available.filter(row=>row.position===player.position&&(row.productionTier??0)>productionTier).sort((a,b)=>(a.productionTier??999)-(b.productionTier??999)||b.projectedPoints-a.projectedPoints)[0]:undefined;
    const tierDropPoints=nextTierPlayer?Math.max(0,player.projectedPoints-nextTierPlayer.projectedPoints):0;
    const strategyAdjustment=player.strategyAdjustment??0;
    const strategyOutcomeAdjustment=Math.max(-.01,Math.min(.01,strategyAdjustment*.001));
    const scarcityOutcomeAdjustment=tierDropPoints>=5&&tierRemaining<=3?.003:0;
    const adjustedDeltas=deltas.map(value=>value+strategyOutcomeAdjustment+scarcityOutcomeAdjustment);
    const scenarioSupport=adjustedDeltas.filter(value=>value>0).length/adjustedDeltas.length,expectedEquityDelta=median(adjustedDeltas);
    const preferenceBoost=player.preference==="target"?1.5:player.preference==="avoid"?-2:0;
    const priorityScore=expectedEquityDelta*1000+scenarioSupport+Math.min(2,tierDropPoints/12)+Math.min(2,Math.max(0,4-tierRemaining)*.4)+strategyAdjustment*.08+preferenceBoost;
    const targetPrice=purchasePrice,walkawayCeiling=Math.max(1,Math.min(maxBid,Math.round(Math.max(targetPrice,player.strategyValue??targetPrice))));
    const impactBand=band(adjustedDeltas);
    return {player,priorityScore,targetPrice,walkawayCeiling,expectedEquityDelta,scenarioSupport,productionTier,tierRemaining,tierDropPoints,nextTierPlayer,impactBand};
  }).sort((a,b)=>b.priorityScore-a.priorityScore||b.expectedEquityDelta-a.expectedEquityDelta||b.player.projectedPoints-a.player.projectedPoints);
  const impacts:DraftImpact[]=evaluated.map(row=>{
    const supportCount=Math.round(row.scenarioSupport*9),role=rosterRole(renegades,row.player.position);
    const scarcity=row.productionTier?`${row.tierRemaining} ${row.player.position} Tier ${row.productionTier} player${row.tierRemaining===1?"":"s"} remain`:`${row.player.position} supply is included`;
    const strategy=row.player.strategyReasons?.[0];
    return {playerId:row.player.id,price:row.targetPrice,band:row.impactBand,label:impactLabels[row.impactBand],expectedEquityDelta:row.expectedEquityDelta,scenarioSupport:row.scenarioSupport,role,
      summary:`At $${row.targetPrice}, buying creates a better projected final roster in ${supportCount} of 9 tested draft paths. ${role}. ${scarcity}.${strategy?` ${strategy}.`:""}`};
  });
  for(const player of available.filter(player=>player.expectedPrice>maxBid))impacts.push({playerId:player.id,price:Math.round(player.expectedPrice),band:"strong_pass",label:"Bad Add",expectedEquityDelta:0,scenarioSupport:0,role:rosterRole(renegades,player.position),summary:`At $${Math.round(player.expectedPrice)}, this player is above the Renegades' current maximum legal bid of $${maxBid}.`});
  const targets=evaluated.slice(0,8).map((row,index)=>{
    const fallback=evaluated.slice(index+1).find(item=>item.player.position===row.player.position);
    const strategyReasons=row.player.strategyReasons??[];
    const priceDecision=nominationDecision(teams,renegadesId,available,row.player.id,maxBid);
    const walkawayCeiling=priceDecision?.recommendedMax??row.targetPrice;
    const why=[`${Math.round(row.scenarioSupport*9)} of 9 roster paths support the target price`,row.productionTier?`${row.tierRemaining} ${row.player.position}${row.productionTier} player${row.tierRemaining===1?"":"s"} remain`:null,row.tierDropPoints>=5?`${row.tierDropPoints.toFixed(1)}-point drop to the next tier`:null,strategyReasons[0]??null].filter(Boolean).join(" · ");
    return {rank:index+1,playerId:row.player.id,name:row.player.name,position:row.player.position,role:rosterRole(renegades,row.player.position),targetPrice:row.targetPrice,walkawayCeiling,expectedEquityDelta:row.expectedEquityDelta,scenarioSupport:row.scenarioSupport,productionTier:row.productionTier,tierRemaining:row.tierRemaining,tierDropPoints:Number(row.tierDropPoints.toFixed(1)),replacementPlayer:fallback?.player.name??row.nextTierPlayer?.name??null,replacementPrice:fallback?.targetPrice??(row.nextTierPlayer?Math.round(row.nextTierPlayer.expectedPrice):null),why,conditionalPlan:`The plan is supported through $${walkawayCeiling}; above that, reassess the remaining roster${fallback?` against ${fallback.player.name} around $${fallback.targetPrice}`:" and the value of preserving budget flexibility"}.`,strategyReasons};
  });
  return {targets,impacts};
}

export function upcomingTargets(teams:DecisionTeam[],renegadesId:string,available:DecisionPlayer[],maxBid:number):UpcomingTarget[]{
  return draftRoadmap(teams,renegadesId,available,maxBid).targets;
}

export function liveLeaderboard(teams:DecisionTeam[],available:DecisionPlayer[]){
  const values:Record<string,number[]>={};for(const team of teams)values[team.id]=[];
  for(const row of baselineScenarioScores(teams,available)){
    const equities=equity(row.scores);for(const team of teams)(values[team.id]??=[]).push(equities[team.id]??0);
  }
  return teams.map(team=>{
    const samples=values[team.id]??[0];return {teamId:team.id,name:team.name,owner:team.owner,
      championshipEquity:samples.reduce((sum,value)=>sum+value,0)/samples.length,
      equityLow:percentile(samples,.1),equityHigh:percentile(samples,.9),projectedLineupPoints:lineupPoints(completeRoster(team,available,"expected","lineup")?.players??team.roster)};
  }).sort((a,b)=>b.championshipEquity-a.championshipEquity).map((row,index)=>({...row,rank:index+1}));
}

function rationale(player:DecisionPlayer,currentPrice:number,recommendation:DecisionBand,recommendedMax:number|null,tierRemaining:number){
  const pursue=recommendation==="strong_pursue"||recommendation==="lean_pursue";
  const tierRead=player.productionTier?` He is production Tier ${player.productionTier}, with ${tierRemaining} player${tierRemaining===1?"":"s"} from that tier still available.`:"";
  return {
    draftBecause:(pursue?`At $${currentPrice}, ${player.name} improves most tested ways to complete the Renegades roster without exhausting later flexibility.`:`If the room stops below $${recommendedMax??currentPrice}, ${player.name}'s projected lineup impact can justify the opportunity cost.`)+tierRead,
    dontDraftBecause:pursue?`Above $${recommendedMax??currentPrice}, later roster paths lose too much budget and comparable alternatives become stronger.`:`At $${currentPrice}, keeping the money creates stronger or statistically indistinguishable completion paths.`,
  };
}

export function nominationDecision(teams:DecisionTeam[],renegadesId:string,available:DecisionPlayer[],playerId:string,maxBid:number){
  const player=available.find(row=>row.id===playerId);const renegades=teams.find(team=>team.id===renegadesId);
  if(!player||!renegades)return null;
  const expected=Math.max(1,Math.round(player.expectedPrice));
  const marketHigh=Math.max(expected,Math.round(player.priceHigh));
  const stretchCeiling=marketHigh+Math.max(2,Math.ceil(expected*.08));
  const extremeCeiling=marketHigh+Math.max(5,Math.ceil(expected*.18));
  const evaluatedMax=Math.min(maxBid,extremeCeiling+Math.max(2,Math.ceil(expected*.05)));
  const poolWithout=available.filter(row=>row.id!==playerId),baseline=baselineScenarioScores(teams,poolWithout);
  const atPrice=[] as {price:number;band:DecisionBand;medianDelta:number;support:number;equityLow:number;equityHigh:number}[];
  let previousDeltas:number[]|null=null;
  for(let purchasePrice=1;purchasePrice<=evaluatedMax;purchasePrice++){
    const deltas:number[]=[],buyEquities:number[]=[];
    for(const row of baseline){
      const passEquity=equity(row.scores)[renegadesId]??0;
      const buyingTeam={...renegades,remainingBudget:renegades.remainingBudget-purchasePrice,openSlots:renegades.openSlots-1,roster:[...renegades.roster,player]};
      const completion=completeRoster(buyingTeam,poolWithout,row.scenario,row.objective);const buyScores={...row.scores,[renegadesId]:completion?.projectedLineupPoints??lineupPoints(buyingTeam.roster)};
      const buyEquity=equity(buyScores)[renegadesId]??0;buyEquities.push(buyEquity);deltas.push(buyEquity-passEquity);
    }
    const prior=previousDeltas;const monotonicDeltas:number[]=prior?deltas.map((value:number,index:number)=>Math.min(value,prior[index]??value)):deltas;
    previousDeltas=monotonicDeltas;
    const sorted=[...monotonicDeltas].sort((a,b)=>a-b);let recommendation=band(monotonicDeltas);
    const openAfterPurchase=Math.max(0,renegades.openSlots-1);
    const flexibleDollars=Math.max(0,renegades.remainingBudget-purchasePrice-openAfterPurchase);
    const startingFlexibleDollars=Math.max(1,renegades.remainingBudget-renegades.openSlots);
    const flexibilityRemaining=flexibleDollars/startingFlexibleDollars;
    if(purchasePrice>extremeCeiling||flexibilityRemaining<.15)recommendation="strong_pass";
    else if(purchasePrice>stretchCeiling||flexibilityRemaining<.3)recommendation="lean_pass";
    else if(purchasePrice>marketHigh&&(recommendation==="strong_pursue"||recommendation==="lean_pursue"))recommendation="neutral";
    atPrice.push({price:purchasePrice,band:recommendation,medianDelta:sorted[Math.floor(sorted.length/2)]??0,support:monotonicDeltas.filter(value=>value>0).length/monotonicDeltas.length,equityLow:percentile(buyEquities,.1),equityHigh:percentile(buyEquities,.9)});
  }
  const tiers:{from:number;to:number;band:DecisionBand}[]=[];
  for(const row of atPrice){const previous=tiers.at(-1);if(previous?.band===row.band)previous.to=row.price;else tiers.push({from:row.price,to:row.price,band:row.band});}
  const baselineRecommendedMax=Math.max(0,...atPrice.filter(row=>row.band==="strong_pursue"||row.band==="lean_pursue").map(row=>row.price))||null;
  const preferenceAdjustment=Math.round(player.strategyAdjustment??0);
  const recommendedMax=baselineRecommendedMax==null?null:Math.max(1,Math.min(maxBid,evaluatedMax,baselineRecommendedMax+preferenceAdjustment));
  const currentPrice=Math.max(1,Math.round(player.expectedPrice)),current=atPrice[Math.min(atPrice.length-1,currentPrice-1)]??atPrice.at(-1)!;
  const productionTierRemaining=player.productionTier?available.filter(row=>row.position===player.position&&row.productionTier===player.productionTier).length:0;
  const auctionTierRemaining=player.auctionTier?available.filter(row=>row.position===player.position&&row.auctionTier===player.auctionTier).length:0;
  const nextProductionTier=player.productionTier?available.filter(row=>row.position===player.position&&(row.productionTier??0)>player.productionTier!).sort((a,b)=>(a.productionTier??999)-(b.productionTier??999)||b.projectedPoints-a.projectedPoints)[0]:undefined;
  return {...current,recommendedMax,baselineRecommendedMax,preferenceAdjustment,tiers,evaluatedMax,marketHigh,stretchCeiling,extremeCeiling,
    tierContext:{productionTier:player.productionTier??null,productionTierRemaining,auctionTier:player.auctionTier??null,auctionTierRemaining,nextProductionTierPlayer:nextProductionTier?.name??null,nextProductionTier:nextProductionTier?.productionTier??null},
    rationale:rationale(player,currentPrice,current.band,recommendedMax,productionTierRemaining),modelStatus:"shadow" as const,
    explanation:"Market-aware read across nine roster-completion paths. Prices above the expected market range are downgraded to protect budget flexibility."};
}
