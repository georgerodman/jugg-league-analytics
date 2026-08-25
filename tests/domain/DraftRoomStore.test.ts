import test from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

test("draft-room view and commands run against isolated local state",async()=>{
  const directory=mkdtempSync(join(tmpdir(),"renegade-draft-room-"));
  process.env.RENEGADE_DB_PATH=join(directory,"draft.sqlite");
  const {applyDraftAction,readDraftRoom,resetDraftRoom}=await import("../../src/server/draftStore.js");
  try{
    const setup=readDraftRoom();
    assert.equal(setup.players.length,294);
    assert.equal(setup.teams.length,10);
    assert.equal(setup.renegades?.name,"Rodman Renegades");
    assert.deepEqual(setup.nominationOrder.teams.map(row=>row.owner),[...setup.nominationOrder.teams.map(row=>row.owner)].sort((a,b)=>a.localeCompare(b,undefined,{sensitivity:"base"})));
    assert.equal(setup.nominationOrder.nextTeamId,setup.nominationOrder.teams[0]?.teamId);
    assert.ok(setup.players.some(row=>row.marketAdp!==null));
    assert.ok(setup.players.some(row=>row.byeWeek!==null));
    assert.deepEqual(setup.draft.recoveryIssues,[]);

    const active=applyDraftAction({type:"start"});
    assert.equal(active.draft.status,"active");
    const reversed=applyDraftAction({type:"updateNominationOrder",teamIds:[...active.nominationOrder.teams.map(row=>row.teamId)].reverse()});
    assert.equal(reversed.nominationOrder.teams[0]?.teamId,active.nominationOrder.teams.at(-1)?.teamId);
    const player=active.players.find(row=>row.status==="available");
    assert.ok(player);
    const preferred=applyDraftAction({type:"playerPreference",playerId:player.id,preference:"avoid",premium:0,note:"test preference"});
    const avoided=preferred.players.find(row=>row.id===player.id)!;
    assert.equal(avoided.status,"available");
    assert.equal(avoided.preference,"avoid");
    assert.ok(avoided.strategyValue!<avoided.productionValue!);
    const withTeamRule=applyDraftAction({type:"updateStrategy",strategy:{buildStyle:"balanced",riskTolerance:"balanced",byeWeekMode:"soft",maxSameBye:2,targetPremium:3,situations:[],teamPreferences:[{team:player.nflTeam!,position:player.position,preference:"prefer",adjustment:2,note:"test team preference"}],notes:""}});
    assert.equal(withTeamRule.strategy.teamPreferences.length,1);
    const nominated=applyDraftAction({type:"nominate",playerId:player.id});
    assert.equal(nominated.currentNomination?.playerId,player.id);
    assert.ok(nominated.currentNomination?.championshipDecision?.tiers.length);
    assert.ok(nominated.currentNomination?.competition.length);
    assert.ok(nominated.currentNomination?.alternatives.length);
    assert.ok(nominated.currentNomination?.decisionPlan);
    assert.ok(nominated.upcomingTargets.length);
    assert.ok(nominated.leaderboard.length===10);
    const sold=applyDraftAction({type:"sale",winnerTeamId:active.renegades!.id,price:1});
    assert.equal(sold.recentSales.length,1);
    assert.equal(sold.renegades!.remainingBudget,199);
    assert.equal(sold.market.salesCount,1);
    assert.notEqual(sold.market.globalMultiplier,1);
    const recentSales=sold.recentSales as {id:string}[];
    const restored=applyDraftAction({type:"voidSale",saleId:recentSales[0]!.id});
    assert.equal(restored.recentSales.length,0);
    assert.equal(restored.renegades!.remainingBudget,200);
    assert.deepEqual(restored.draft.recoveryIssues,[]);
    const reset=resetDraftRoom({preservePreferences:true});
    const clean=readDraftRoom();
    assert.ok(existsSync(reset.backupPath));
    assert.equal(clean.draft.status,"setup");
    assert.equal(clean.draft.stateVersion,0);
    assert.equal(clean.recentSales.length,0);
    assert.equal(clean.players.find(row=>row.id===player.id)?.preference,"avoid");
  }finally{
    globalThis.__renegadeDraftService?.db.close();
    globalThis.__renegadeDraftService=undefined;
    rmSync(directory,{recursive:true,force:true});
  }
});
