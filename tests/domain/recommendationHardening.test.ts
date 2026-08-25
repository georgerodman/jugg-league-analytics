import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { draftRoadmap, nominationDecision, type DecisionBand, type DecisionPlayer, type DecisionTeam } from "../../src/domain/liveDecisionEngine.js";

const pointer=JSON.parse(readFileSync("data/processed/production_value_model/latest.json","utf8"));
const board=JSON.parse(readFileSync(pointer.decision_board_json,"utf8"));
const players:DecisionPlayer[]=board.players.map((row:any)=>({id:row.internal_player_id,name:row.player_name,position:row.position,projectedPoints:Number(row.projected_points),expectedPrice:Number(row.expected_jugg_price),priceLow:Number(row.price_range_low),priceHigh:Number(row.price_range_high),productionTier:row.production_tier,auctionTier:row.auction_tier,pointsAboveReplacement:row.points_above_replacement,replacementPoints:row.replacement_points,strategyValue:row.production_value}));
const teams:DecisionTeam[]=Array.from({length:10},(_,index)=>({id:`team-${index}`,name:index===0?"Rodman Renegades":`Team ${index}`,owner:`Owner ${index}`,remainingBudget:200,openSlots:14,roster:[]}));
const order:Record<DecisionBand,number>={strong_pursue:0,lean_pursue:1,neutral:2,lean_pass:3,strong_pass:4};

function bandAt(tiers:{from:number;to:number;band:DecisionBand}[],price:number){return tiers.find(tier=>price>=tier.from&&price<=tier.to)?.band;}

test("Walk-Away boundary separates pursue from non-pursue without a favorable reversal",()=>{
  const candidate=players.map(player=>nominationDecision(teams,"team-0",players,player.id,187)).find(decision=>decision?.recommendedMax&&decision.recommendedMax<decision.evaluatedMax);
  assert.ok(candidate?.recommendedMax);
  const below=bandAt(candidate.tiers,Math.max(1,candidate.recommendedMax-1));
  const at=bandAt(candidate.tiers,candidate.recommendedMax);
  const above=bandAt(candidate.tiers,candidate.recommendedMax+1);
  assert.ok(below&&at&&above);
  assert.ok(order[below]<=order[at]&&order[at]<=order[above]);
  assert.ok(at==="strong_pursue"||at==="lean_pursue");
  assert.ok(above!=="strong_pursue"&&above!=="lean_pursue");
});

test("a sold advertised fallback is removed and the roadmap recalculates",()=>{
  const before=draftRoadmap(teams,"team-0",players,187);
  const target=before.targets.find(row=>row.replacementPlayer);
  assert.ok(target?.replacementPlayer);
  const afterPool=players.filter(player=>player.name!==target.replacementPlayer);
  const after=draftRoadmap(teams,"team-0",afterPool,187);
  assert.ok(after.targets.every(row=>row.replacementPlayer!==target.replacementPlayer));
});

test("the packet reports unique supply when a production tier has one player",()=>{
  const selected={...players.find(player=>player.position==="TE")!,productionTier:999};
  const pool=[selected,...players.filter(player=>player.id!==selected.id)];
  const decision=nominationDecision(teams,"team-0",pool,selected.id,187);
  assert.ok(decision);
  assert.equal(decision.tierContext.productionTierRemaining,1);
  assert.equal(decision.tierContext.nextProductionTierPlayer,null);
});

test("the roadmap is honest when no same-position fallback exists",()=>{
  const selected={...players.find(player=>player.position==="QB")!,projectedPoints:1000,expectedPrice:1,priceLow:1,priceHigh:2,pointsAboveReplacement:900,strategyAdjustment:10_000,preference:"target" as const};
  const pool=[selected,...players.filter(player=>player.position!=="QB")];
  const settledTeams=teams.map((team,index)=>index===0?team:{...team,openSlots:13,roster:[{...selected,id:`settled-qb-${index}`,name:`Settled QB ${index}`,projectedPoints:250}]});
  const roadmap=draftRoadmap(settledTeams,"team-0",pool,187);
  const target=roadmap.targets.find(row=>row.playerId===selected.id);
  assert.ok(target);
  assert.equal(target.replacementPlayer,null);
  assert.equal(target.replacementPrice,null);
});

test("the deterministic recommendation packet contains every review-critical field",()=>{
  for(const player of players.slice(0,24)){
    const decision=nominationDecision(teams,"team-0",players,player.id,187);
    assert.ok(decision);
    assert.equal(decision.tiers[0]?.from,1);
    assert.equal(decision.tiers.at(-1)?.to,decision.evaluatedMax);
    assert.ok(decision.marketHigh>=Math.round(player.expectedPrice));
    assert.ok(decision.tierContext.productionTierRemaining>=1);
    assert.equal(decision.modelStatus,"shadow");
    assert.ok(decision.explanation.length>30);
    assert.ok(decision.rationale.draftBecause.length>30);
    assert.ok(decision.rationale.dontDraftBecause.length>30);
  }
});
