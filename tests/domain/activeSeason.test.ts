import assert from "node:assert/strict";
import test from "node:test";
import { activeSeason, activeSeasonPaths, activeSeasonSchema } from "../../src/server/activeSeason";

test("active season configuration is internally consistent and locally scoped",()=>{
  assert.equal(activeSeason.draftId,`jugg-${activeSeason.season}`);
  assert.match(activeSeason.databasePath,/^\.local\//);
  assert.match(activeSeason.googleSheetsConfigPath,/^config\//);
  assert.match(activeSeasonPaths.canonicalProjections,new RegExp(`/${activeSeason.season}/latest\\.json$`));
});

test("active season configuration rejects cross-season and unsafe paths",()=>{
  const base={schemaVersion:1 as const,season:2027,draftId:"jugg-2027",draftName:"2027 JUGG Auction",databasePath:".local/renegade-draft-room-2027.sqlite",googleSheetsConfigPath:"config/google_sheets_2027.json"};
  assert.equal(activeSeasonSchema.safeParse({...base,draftId:"jugg-2026"}).success,false);
  assert.equal(activeSeasonSchema.safeParse({...base,databasePath:"/tmp/draft.sqlite"}).success,false);
  assert.equal(activeSeasonSchema.safeParse({...base,googleSheetsConfigPath:"../google.json"}).success,false);
});
