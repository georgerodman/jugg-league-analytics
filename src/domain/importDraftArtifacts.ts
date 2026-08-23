import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import type { DraftService, PlayerInput, SlotTemplate, TeamInput } from "./DraftService.js";

export const JUGG_SLOTS: SlotTemplate[] = [
  {slotType:"QB",count:1,eligiblePositions:["QB"]},{slotType:"WR",count:2,eligiblePositions:["WR"]},
  {slotType:"RB",count:1,eligiblePositions:["RB"]},{slotType:"WR_RB",count:1,eligiblePositions:["WR","RB"]},
  {slotType:"WR_RB_TE",count:1,eligiblePositions:["WR","RB","TE"]},{slotType:"TE",count:1,eligiblePositions:["TE"]},
  {slotType:"K",count:1,eligiblePositions:["K"]},{slotType:"DEF",count:1,eligiblePositions:["DEF"]},
  {slotType:"BN",count:5,eligiblePositions:["QB","RB","WR","TE","K","DEF"]},
];

function file(path:string){const bytes=readFileSync(path);return {bytes,payload:JSON.parse(bytes.toString("utf8")),sha256:createHash("sha256").update(bytes).digest("hex")};}

export function initializeFromArtifacts(service:DraftService,input:{draftId:string;season:number;name:string;decisionBoardPath:string;ownerProfilesPath:string;teamNames?:Record<string,string>}):void {
  const board=file(input.decisionBoardPath), owners=file(input.ownerProfilesPath);
  const teams:TeamInput[]=owners.payload.owners.map((profile:any,index:number)=>({id:`team:${index+1}`,ownerId:`owner:${profile.owner.toLowerCase().replace(/[^a-z0-9]+/g,"-")}`,ownerName:profile.owner,name:input.teamNames?.[profile.owner] ?? profile.owner}));
  const players:PlayerInput[]=board.payload.players.map((row:any)=>({id:row.internal_player_id,name:row.player_name,position:row.position,nflTeam:row.nfl_team,identityStatus:row.internal_player_id.startsWith("provisional:")?"provisional":"stable"}));
  service.initializeDraft({id:input.draftId,season:input.season,name:input.name,teams,players,slots:JUGG_SLOTS});
  service.db.transaction(()=>{
    service.db.prepare("INSERT INTO artifact_imports(id,artifact_type,schema_version,build_id,relative_path,sha256,metadata_json) VALUES(?,?,?,?,?,?,?)").run("artifact:decision","combined_decision_board",1,board.payload.metadata.build_id,input.decisionBoardPath,board.sha256,JSON.stringify(board.payload.metadata));
    service.db.prepare("INSERT INTO artifact_imports(id,artifact_type,schema_version,build_id,relative_path,sha256,metadata_json) VALUES(?,?,?,?,?,?,?)").run("artifact:owners","owner_tendencies",1,owners.payload.metadata.build_id,input.ownerProfilesPath,owners.sha256,JSON.stringify(owners.payload.metadata));
    const update=service.db.prepare("UPDATE draft_player_pool SET expected_price=?,price_low=?,price_high=?,draft_probability=?,production_value=?,expected_surplus=?,risk_flags_json=?,market_artifact_id='artifact:decision',production_artifact_id='artifact:decision',owner_profile_artifact_id='artifact:owners' WHERE draft_id=? AND player_id=?");
    for(const row of board.payload.players) update.run(row.expected_jugg_price,row.price_range_low,row.price_range_high,row.draft_probability,row.production_value,row.expected_surplus,JSON.stringify((row.risk_flags||"").split(";").filter(Boolean)),input.draftId,row.internal_player_id);
  })();
}
