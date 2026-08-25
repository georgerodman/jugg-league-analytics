import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("published simulation baseline preserves core accounting and isolation evidence",()=>{
  const latest=JSON.parse(readFileSync("data/processed/draft_simulations/latest.json","utf8"));
  const baseline=JSON.parse(readFileSync(latest.artifact,"utf8"));
  assert.equal(baseline.summary.completed,baseline.summary.runs);
  assert.equal(baseline.summary.legal,baseline.summary.runs);
  assert.equal(baseline.summary.checks.recoveryEquivalent,true);
  for(const scenario of baseline.scenarios){
    assert.equal(scenario.sales,140);
    assert.equal(scenario.budgetConservation,true);
    assert.equal(scenario.actions.at(-1).renegades.openSlots,0);
    assert.ok(scenario.actions.every((action:any)=>action.stateVersion===action.sale*2+1));
  }
});

test("baseline records the known non-monotonic price-band finding",()=>{
  const latest=JSON.parse(readFileSync("data/processed/draft_simulations/latest.json","utf8"));
  const baseline=JSON.parse(readFileSync(latest.artifact,"utf8"));
  assert.equal(baseline.summary.checks.priceBandMonotonic,false,
    "remove this expectation only after an approved policy fix and new-seed evaluation");
});
