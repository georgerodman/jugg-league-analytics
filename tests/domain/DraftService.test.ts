import test from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import { readFileSync } from "node:fs";
import { DraftService, DomainError, type SlotTemplate } from "../../src/domain/DraftService.js";
import { initializeFromArtifacts, JUGG_SLOTS } from "../../src/domain/importDraftArtifacts.js";

const migration=readFileSync("db/migrations/001_initial.sql","utf8")+readFileSync("db/migrations/002_strategy_and_market_context.sql","utf8")+readFileSync("db/migrations/003_nomination_and_waiver_order.sql","utf8")+readFileSync("db/migrations/004_decision_planning.sql","utf8")+readFileSync("db/migrations/005_nomination_owner_changed_event.sql","utf8");
const slots:SlotTemplate[]=[
  {slotType:"QB",count:1,eligiblePositions:["QB"]},{slotType:"RB",count:1,eligiblePositions:["RB"]},
  {slotType:"WR",count:2,eligiblePositions:["WR"]},{slotType:"TE",count:1,eligiblePositions:["TE"]},
  {slotType:"WR_RB",count:1,eligiblePositions:["WR","RB"]},{slotType:"WR_RB_TE",count:1,eligiblePositions:["WR","RB","TE"]},
  {slotType:"K",count:1,eligiblePositions:["K"]},{slotType:"DEF",count:1,eligiblePositions:["DEF"]},
  {slotType:"BN",count:5,eligiblePositions:["QB","RB","WR","TE","K","DEF"]},
];

function service(){const db=new Database(":memory:");db.exec(migration);const svc=new DraftService(db);svc.initializeDraft({id:"d",season:2026,name:"JUGG",teams:[{id:"t",ownerId:"o",ownerName:"Owner",name:"Team"},{id:"t2",ownerId:"o2",ownerName:"Owner 2",name:"Team 2"}],players:[{id:"p",name:"Runner",position:"RB",identityStatus:"stable"},{id:"w",name:"Receiver",position:"WR",identityStatus:"stable"}],slots});return svc;}
const at="2026-08-23T20:00:00Z";

test("records a sale atomically and preserves budget reserves",()=>{
  const svc=service();svc.startDraft({draftId:"d",expectedVersion:0,idempotencyKey:"start",occurredAt:at});
  svc.openNomination({draftId:"d",expectedVersion:1,idempotencyKey:"nom",occurredAt:at,playerId:"p"});
  const result=svc.recordSale({draftId:"d",expectedVersion:2,idempotencyKey:"sale",occurredAt:at,winnerTeamId:"t",price:50}) as any;
  assert.ok(result.saleId);assert.deepEqual(svc.recoveryAudit("d"),[]);
  const state=svc.db.prepare("SELECT * FROM team_draft_state WHERE team_id='t'").get() as any;
  assert.equal(state.remaining_budget,150);assert.equal(state.open_slot_count,13);assert.equal(state.rostered_player_count,1);
  assert.equal((svc.db.prepare("SELECT status FROM draft_player_pool WHERE player_id='p'").get() as any).status,"sold");
  assert.equal((svc.db.prepare("SELECT COUNT(*) count FROM sync_outbox").get() as any).count,3);
});

test("rejects a sale that consumes required one-dollar reserves",()=>{
  const svc=service();svc.startDraft({draftId:"d",expectedVersion:0,idempotencyKey:"start",occurredAt:at});
  svc.openNomination({draftId:"d",expectedVersion:1,idempotencyKey:"nom",occurredAt:at,playerId:"p"});
  assert.throws(()=>svc.recordSale({draftId:"d",expectedVersion:2,idempotencyKey:"sale",occurredAt:at,winnerTeamId:"t",price:188}),
    (error:any)=>error instanceof DomainError&&error.code==="BUDGET_RESERVE");
  assert.equal((svc.db.prepare("SELECT COUNT(*) count FROM sales").get() as any).count,0);
  assert.equal((svc.db.prepare("SELECT COUNT(*) count FROM draft_events").get() as any).count,2);
});

test("a rejected sale rolls back the entire action boundary",()=>{
  const svc=service();svc.startDraft({draftId:"d",expectedVersion:0,idempotencyKey:"start",occurredAt:at});
  svc.openNomination({draftId:"d",expectedVersion:1,idempotencyKey:"nom",occurredAt:at,playerId:"p"});
  const before={draft:svc.db.prepare("SELECT state_version FROM drafts WHERE id='d'").get(),nomination:svc.db.prepare("SELECT status FROM nominations WHERE draft_id='d'").get(),pool:svc.db.prepare("SELECT status FROM draft_player_pool WHERE player_id='p'").get(),events:(svc.db.prepare("SELECT COUNT(*) count FROM draft_events").get() as any).count,outbox:(svc.db.prepare("SELECT COUNT(*) count FROM sync_outbox").get() as any).count};
  assert.throws(()=>svc.recordSale({draftId:"d",expectedVersion:2,idempotencyKey:"interrupted-sale",occurredAt:at,winnerTeamId:"t",price:188}),
    (error:any)=>error instanceof DomainError&&error.code==="BUDGET_RESERVE");
  const after={draft:svc.db.prepare("SELECT state_version FROM drafts WHERE id='d'").get(),nomination:svc.db.prepare("SELECT status FROM nominations WHERE draft_id='d'").get(),pool:svc.db.prepare("SELECT status FROM draft_player_pool WHERE player_id='p'").get(),events:(svc.db.prepare("SELECT COUNT(*) count FROM draft_events").get() as any).count,outbox:(svc.db.prepare("SELECT COUNT(*) count FROM sync_outbox").get() as any).count};
  assert.deepEqual(after,before);assert.deepEqual(svc.recoveryAudit("d"),[]);
});

test("records a Renegades purchase above the walk-away price without blocking the sale",()=>{
  const svc=service();
  svc.db.prepare("UPDATE teams SET display_name='Rodman Renegades' WHERE id='t'").run();
  svc.startDraft({draftId:"d",expectedVersion:0,idempotencyKey:"start",occurredAt:at});
  svc.openNomination({draftId:"d",expectedVersion:1,idempotencyKey:"nom",occurredAt:at,playerId:"p"});
  const nomination=svc.db.prepare("SELECT id FROM nominations WHERE draft_id='d' AND status='open'").get() as {id:string};
  svc.db.prepare("INSERT INTO nomination_decision_plans(nomination_id,draft_id,player_id,recommended_ceiling,committed_ceiling) VALUES(?,?,?,?,?)").run(nomination.id,"d","p",30,35);
  svc.recordSale({draftId:"d",expectedVersion:2,idempotencyKey:"sale-no-reason",occurredAt:at,winnerTeamId:"t",price:40});
  const override=svc.db.prepare("SELECT actual_price actualPrice,committed_ceiling committedCeiling,reason FROM discipline_overrides").get() as any;
  assert.deepEqual(override,{actualPrice:40,committedCeiling:35,reason:"No reason recorded"});
});

test("idempotency replays and stale versions fail",()=>{
  const svc=service();const first=svc.startDraft({draftId:"d",expectedVersion:0,idempotencyKey:"start",occurredAt:at}) as any;
  const replay=svc.startDraft({draftId:"d",expectedVersion:0,idempotencyKey:"start",occurredAt:at}) as any;
  assert.equal(replay.eventId,first.eventId);assert.equal(replay.replayed,true);
  assert.throws(()=>svc.openNomination({draftId:"d",expectedVersion:0,idempotencyKey:"stale",occurredAt:at,playerId:"p"}),
    (error:any)=>error instanceof DomainError&&error.code==="VERSION_CONFLICT");
});

test("correcting a nomination owner is audited and persists",()=>{
  const svc=service();svc.startDraft({draftId:"d",expectedVersion:0,idempotencyKey:"start",occurredAt:at});
  svc.openNomination({draftId:"d",expectedVersion:1,idempotencyKey:"nom",occurredAt:at,playerId:"p",nominatedByTeamId:"t"});
  svc.changeNominationOwner({draftId:"d",expectedVersion:2,idempotencyKey:"owner-fix",occurredAt:at,nominatedByTeamId:"t2"});
  assert.equal((svc.db.prepare("SELECT nominated_by_team_id teamId FROM nominations WHERE draft_id='d' AND status='open'").get() as any).teamId,"t2");
  assert.equal((svc.db.prepare("SELECT event_type eventType FROM draft_events WHERE sequence=3").get() as any).eventType,"nomination_owner_changed");
  assert.deepEqual(svc.recoveryAudit("d"),[]);
});

test("voiding a sale restores roster, budget, and availability",()=>{
  const svc=service();svc.startDraft({draftId:"d",expectedVersion:0,idempotencyKey:"start",occurredAt:at});
  svc.openNomination({draftId:"d",expectedVersion:1,idempotencyKey:"nom",occurredAt:at,playerId:"p"});
  const sale=svc.recordSale({draftId:"d",expectedVersion:2,idempotencyKey:"sale",occurredAt:at,winnerTeamId:"t",price:50}) as any;
  svc.voidSale({draftId:"d",expectedVersion:3,idempotencyKey:"void",occurredAt:at,saleId:sale.saleId});
  const state=svc.db.prepare("SELECT * FROM team_draft_state WHERE team_id='t'").get() as any;
  assert.equal(state.remaining_budget,200);assert.equal(state.open_slot_count,14);assert.equal(state.rostered_player_count,0);
  assert.equal((svc.db.prepare("SELECT status FROM draft_player_pool WHERE player_id='p'").get() as any).status,"available");
  assert.deepEqual(svc.recoveryAudit("d"),[]);
});

test("reassigns a player to a legal slot and keeps corrections consistent",()=>{
  const svc=service();svc.startDraft({draftId:"d",expectedVersion:0,idempotencyKey:"start",occurredAt:at});
  svc.openNomination({draftId:"d",expectedVersion:1,idempotencyKey:"nom",occurredAt:at,playerId:"p"});
  const sale=svc.recordSale({draftId:"d",expectedVersion:2,idempotencyKey:"sale",occurredAt:at,winnerTeamId:"t",price:50}) as any;
  svc.reassignRosterSlot({draftId:"d",expectedVersion:3,idempotencyKey:"move",occurredAt:at,teamId:"t",playerId:"p",targetSlotId:"t:WR_RB:1"});
  assert.equal((svc.db.prepare("SELECT player_id playerId FROM roster_slots WHERE id='t:WR_RB:1'").get() as any).playerId,"p");
  assert.equal((svc.db.prepare("SELECT roster_slot_id slotId FROM sales WHERE id=?").get(sale.saleId) as any).slotId,"t:WR_RB:1");
  svc.voidSale({draftId:"d",expectedVersion:4,idempotencyKey:"void",occurredAt:at,saleId:sale.saleId});
  assert.equal((svc.db.prepare("SELECT player_id playerId FROM roster_slots WHERE id='t:WR_RB:1'").get() as any).playerId,null);
  assert.deepEqual(svc.recoveryAudit("d"),[]);
});

test("rejects an ineligible roster reassignment",()=>{
  const svc=service();svc.startDraft({draftId:"d",expectedVersion:0,idempotencyKey:"start",occurredAt:at});
  svc.openNomination({draftId:"d",expectedVersion:1,idempotencyKey:"nom",occurredAt:at,playerId:"p"});
  svc.recordSale({draftId:"d",expectedVersion:2,idempotencyKey:"sale",occurredAt:at,winnerTeamId:"t",price:50});
  assert.throws(()=>svc.reassignRosterSlot({draftId:"d",expectedVersion:3,idempotencyKey:"bad-move",occurredAt:at,teamId:"t",playerId:"p",targetSlotId:"t:QB:1"}),
    (error:any)=>error instanceof DomainError&&error.code==="INELIGIBLE_ROSTER_SLOT");
});

test("a sale succeeds only for the team with a remaining eligible destination",()=>{
  const svc=service();svc.startDraft({draftId:"d",expectedVersion:0,idempotencyKey:"start",occurredAt:at});
  svc.db.prepare("UPDATE roster_slots SET eligible_positions_json='[\"WR\"]' WHERE team_id='t'").run();
  svc.openNomination({draftId:"d",expectedVersion:1,idempotencyKey:"nom",occurredAt:at,playerId:"p"});
  assert.throws(()=>svc.recordSale({draftId:"d",expectedVersion:2,idempotencyKey:"wrong-team",occurredAt:at,winnerTeamId:"t",price:1}),
    (error:any)=>error instanceof DomainError&&error.code==="NO_ELIGIBLE_SLOT");
  const result=svc.recordSale({draftId:"d",expectedVersion:2,idempotencyKey:"legal-team",occurredAt:at,winnerTeamId:"t2",price:1}) as any;
  assert.ok(result.saleId);assert.deepEqual(svc.recoveryAudit("d"),[]);
});

test("records and reverses draft completion for waiver priority",()=>{
  const svc=service();svc.startDraft({draftId:"d",expectedVersion:0,idempotencyKey:"start",occurredAt:at});
  svc.db.prepare("UPDATE team_draft_state SET open_slot_count=1,rostered_player_count=13 WHERE team_id='t'").run();
  svc.openNomination({draftId:"d",expectedVersion:1,idempotencyKey:"nom",occurredAt:at,playerId:"p",nominatedByTeamId:"t"});
  const sale=svc.recordSale({draftId:"d",expectedVersion:2,idempotencyKey:"sale",occurredAt:at,winnerTeamId:"t",price:50}) as any;
  assert.equal((svc.db.prepare("SELECT COUNT(*) count FROM team_draft_completions WHERE team_id='t' AND voided_event_id IS NULL").get() as any).count,1);
  svc.voidSale({draftId:"d",expectedVersion:3,idempotencyKey:"void",occurredAt:at,saleId:sale.saleId});
  assert.equal((svc.db.prepare("SELECT COUNT(*) count FROM team_draft_completions WHERE team_id='t' AND voided_event_id IS NULL").get() as any).count,0);
});

test("the production slot template contains fourteen draftable slots",()=>{
  assert.equal(JUGG_SLOTS.reduce((sum,slot)=>sum+slot.count,0),14);
});

test("current artifacts initialize the complete offline draft",()=>{
  const production=JSON.parse(readFileSync("data/processed/production_value_model/latest.json","utf8"));
  const owners=JSON.parse(readFileSync("data/processed/owner_tendencies/latest.json","utf8"));
  const db=new Database(":memory:");db.exec(migration);const svc=new DraftService(db);
  initializeFromArtifacts(svc,{draftId:"2026",season:2026,name:"JUGG 2026",decisionBoardPath:production.decision_board_json,ownerProfilesPath:owners.artifact});
  assert.equal((db.prepare("SELECT COUNT(*) count FROM teams").get() as any).count,10);
  assert.equal((db.prepare("SELECT COUNT(*) count FROM roster_slots").get() as any).count,140);
  assert.equal((db.prepare("SELECT COUNT(*) count FROM draft_player_pool").get() as any).count,294);
  assert.equal((db.prepare("SELECT COUNT(*) count FROM artifact_imports").get() as any).count,2);
});
