import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("published simulation baseline preserves core accounting and isolation evidence",()=>{
  const latest=JSON.parse(readFileSync("data/processed/draft_simulations/latest.json","utf8"));
  const baseline=JSON.parse(readFileSync(latest.artifact,"utf8"));
  assert.equal(baseline.summary.completed,baseline.summary.runs);
  assert.equal(baseline.summary.legal,baseline.summary.runs);
  assert.equal(baseline.summary.checks.recoveryEquivalent,true);
  assert.equal(baseline.certified_invariants.scenario_count,baseline.summary.runs);
  assert.equal(baseline.certified_invariants.scenarios_with_140_sales,baseline.summary.runs);
  assert.equal(baseline.certified_invariants.scenarios_with_budget_conservation,baseline.summary.runs);
  assert.equal(baseline.certified_invariants.scenarios_with_zero_final_open_slots,baseline.summary.runs);
  assert.equal(baseline.certified_invariants.scenarios_with_valid_state_versions,baseline.summary.runs);
});

test("baseline records the known non-monotonic price-band finding",()=>{
  const latest=JSON.parse(readFileSync("data/processed/draft_simulations/latest.json","utf8"));
  const baseline=JSON.parse(readFileSync(latest.artifact,"utf8"));
  assert.equal(baseline.summary.checks.priceBandMonotonic,false,
    "remove this expectation only after an approved policy fix and new-seed evaluation");
});
