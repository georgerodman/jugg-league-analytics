import test from "node:test";
import assert from "node:assert/strict";
import { completeRoster, draftRoadmap, liveLeaderboard, nominationDecision, upcomingTargets, type DecisionPlayer, type DecisionTeam } from "../../src/domain/liveDecisionEngine.js";

const players:DecisionPlayer[]=[];
for(const [position,count] of Object.entries({QB:20,RB:45,WR:55,TE:25,K:15,DEF:15}) as [DecisionPlayer["position"],number][]){
  for(let index=0;index<count;index++)players.push({id:`${position}-${index}`,name:`${position} ${index}`,position,projectedPoints:300-index*3,
    expectedPrice:Math.max(1,35-index),priceLow:Math.max(1,30-index),priceHigh:Math.max(1,40-index),productionTier:Math.floor(index/5)+1,auctionTier:Math.floor(index/5)+1});
}
const teams:DecisionTeam[]=Array.from({length:10},(_,index)=>({id:`team-${index}`,name:index===0?"Rodman Renegades":`Team ${index}`,owner:`Owner ${index}`,remainingBudget:200,openSlots:14,roster:[]}));

test("neutral completion creates a full affordable roster",()=>{
  const result=completeRoster(teams[0]!,players,"expected","lineup");
  assert.ok(result);assert.equal(result.players.length,14);assert.ok(result.remainingBudget>=0);
});

test("live leaderboard allocates all championship equity",()=>{
  const board=liveLeaderboard(teams,players);
  assert.equal(board.length,10);assert.ok(Math.abs(board.reduce((sum,row)=>sum+row.championshipEquity,0)-1)<1e-9);
});

test("nomination decision evaluates a realistic market range and protects against extreme prices",()=>{
  const decision=nominationDecision(teams,"team-0",players,players[0]!.id,187);
  assert.ok(decision);assert.ok(decision.tiers.length>=1);assert.equal(decision.tiers[0]!.from,1);assert.equal(decision.tiers.at(-1)!.to,decision.evaluatedMax);
  assert.ok(decision.evaluatedMax<187);assert.equal(decision.tiers.at(-1)!.band,"strong_pass");
  assert.ok(decision.support>=0&&decision.support<=1);
  assert.equal(decision.tierContext.productionTier,1);assert.equal(decision.tierContext.productionTierRemaining,5);
});

test("upcoming targets rank affordable paths and preserve fallbacks",()=>{
  const targets=upcomingTargets(teams,"team-0",players,187);
  assert.equal(targets.length,8);
  assert.deepEqual(targets.map(target=>target.rank),[1,2,3,4,5,6,7,8]);
  assert.ok(targets.every(target=>target.targetPrice<=target.walkawayCeiling&&target.walkawayCeiling<=187));
  assert.ok(targets[0]!.conditionalPlan.length>10);
  assert.ok(targets.slice(0,-1).some(target=>target.replacementPlayer));
  for(const target of targets){
    const decision=nominationDecision(teams,"team-0",players,target.playerId,187);
    assert.equal(target.walkawayCeiling,decision?.recommendedMax);
  }
});

test("draft impact classifies every available player at the expected price",()=>{
  const roadmap=draftRoadmap(teams,"team-0",players,187);
  assert.equal(roadmap.impacts.length,players.length);
  assert.ok(roadmap.impacts.every(impact=>impact.price>=1&&impact.summary.includes(`At $${impact.price}`)));
  assert.ok(roadmap.impacts.every(impact=>["Great Add","Good Add","Neutral","Poor Add","Bad Add"].includes(impact.label)));
  assert.ok(roadmap.impacts.every(impact=>impact.scenarioSupport>=0&&impact.scenarioSupport<=1));
});

test("the shared ceiling applies a visible bounded strategy adjustment",()=>{
  const target={...players[0]!,strategyAdjustment:3};
  const pool=[target,...players.slice(1)];
  const decision=nominationDecision(teams,"team-0",pool,target.id,187);
  assert.ok(decision?.baselineRecommendedMax);
  assert.equal(decision?.preferenceAdjustment,3);
  assert.equal(decision?.recommendedMax,(decision?.baselineRecommendedMax??0)+3);
});
