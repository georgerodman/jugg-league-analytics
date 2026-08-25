import test from "node:test";
import assert from "node:assert/strict";
import { completeRoster, liveLeaderboard, nominationDecision, type DecisionPlayer, type DecisionTeam } from "../../src/domain/liveDecisionEngine.js";

const players:DecisionPlayer[]=[];
for(const [position,count] of Object.entries({QB:20,RB:45,WR:55,TE:25,K:15,DEF:15}) as [DecisionPlayer["position"],number][]){
  for(let index=0;index<count;index++)players.push({id:`${position}-${index}`,name:`${position} ${index}`,position,projectedPoints:300-index*3,
    expectedPrice:Math.max(1,35-index),priceLow:Math.max(1,30-index),priceHigh:Math.max(1,40-index)});
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
});
