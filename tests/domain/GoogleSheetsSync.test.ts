import test from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import { readFileSync } from "node:fs";
import { DraftService, type SlotTemplate } from "../../src/domain/DraftService.js";
import { buildDraftBoardRequests } from "../../src/server/googleSheetsSync.js";

const migration=["001_initial.sql","002_strategy_and_market_context.sql","003_nomination_and_waiver_order.sql","004_decision_planning.sql"].map(file=>readFileSync(`db/migrations/${file}`,"utf8")).join("\n");
const slots:SlotTemplate[]=[{slotType:"QB",count:1,eligiblePositions:["QB"]},{slotType:"WR",count:2,eligiblePositions:["WR"]},{slotType:"RB",count:1,eligiblePositions:["RB"]},{slotType:"TE",count:1,eligiblePositions:["TE"]},{slotType:"WR_RB",count:1,eligiblePositions:["WR","RB"]},{slotType:"WR_RB_TE",count:1,eligiblePositions:["WR","RB","TE"]},{slotType:"DEF",count:1,eligiblePositions:["DEF"]},{slotType:"K",count:1,eligiblePositions:["K"]},{slotType:"BN",count:5,eligiblePositions:["QB","RB","WR","TE","K","DEF"]}];

test("draft board projection writes player and price into the owner's matching slot",()=>{
  const db=new Database(":memory:");db.exec(migration);const service=new DraftService(db);
  service.initializeDraft({id:"d",season:2026,name:"Draft",teams:[{id:"t",ownerId:"o",ownerName:"George Rodman",name:"Rodman Renegades"},{id:"t2",ownerId:"o2",ownerName:"Lee Krassner",name:"Lee Krassner"}],players:[{id:"p",name:"Quarter Back",position:"QB",identityStatus:"stable"}],slots});
  db.prepare("UPDATE drafts SET status='active' WHERE id='d'").run();
  service.openNomination({draftId:"d",expectedVersion:0,idempotencyKey:"n",occurredAt:"2026-01-01",playerId:"p"});
  service.recordSale({draftId:"d",expectedVersion:1,idempotencyKey:"s",occurredAt:"2026-01-01",winnerTeamId:"t",price:12});
  const requests=buildDraftBoardRequests(db,"d",{spreadsheetId:"x",sheetName:"Sheet1",sheetId:0,owners:{"George Rodman":{playerColumn:1,priceColumn:2,firstRosterRow:4},"Lee Krassner":{playerColumn:5,priceColumn:6,firstRosterRow:4}}});
  const update=(requests.find((request:any)=>request.updateCells.range.startColumnIndex===1) as any).updateCells;
  assert.deepEqual(update.range,{sheetId:0,startRowIndex:4,endRowIndex:18,startColumnIndex:1,endColumnIndex:3});
  assert.equal(update.rows[0].values[0].userEnteredValue.stringValue,"Quarter Back");
  assert.equal(update.rows[0].values[1].userEnteredValue.numberValue,12);
  assert.deepEqual(update.rows[1].values,[{},{}]);
  db.close();
});
