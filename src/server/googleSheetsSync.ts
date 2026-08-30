import { createSign } from "node:crypto";
import { readFileSync } from "node:fs";
import type Database from "better-sqlite3";

type SheetOwner={playerColumn:number;priceColumn:number;firstRosterRow:number};
type SheetConfig={spreadsheetId:string;sheetName:string;sheetId:number;owners:Record<string,SheetOwner>};
type ServiceAccount={client_email:string;private_key:string;token_uri?:string};
type CellValue={userEnteredValue?:{stringValue?:string;numberValue?:number}};

const SLOT_ORDER=["QB:1","WR:1","WR:2","RB:1","TE:1","WR_RB:1","WR_RB_TE:1","DEF:1","K:1","BN:1","BN:2","BN:3","BN:4","BN:5"];

function base64url(value:string|Buffer){return Buffer.from(value).toString("base64url");}

function credentials():ServiceAccount|null{
  const inline=process.env.GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON;
  const path=process.env.GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE;
  if(!inline&&!path)return null;
  const parsed=JSON.parse(inline??readFileSync(path!,"utf8")) as Partial<ServiceAccount>;
  if(!parsed.client_email||!parsed.private_key)throw new Error("Google Sheets service-account credentials are incomplete");
  return parsed as ServiceAccount;
}

async function accessToken(account:ServiceAccount):Promise<string>{
  const now=Math.floor(Date.now()/1000),header=base64url(JSON.stringify({alg:"RS256",typ:"JWT"}));
  const claims=base64url(JSON.stringify({iss:account.client_email,scope:"https://www.googleapis.com/auth/spreadsheets",aud:account.token_uri??"https://oauth2.googleapis.com/token",iat:now,exp:now+3600}));
  const unsigned=`${header}.${claims}`,signer=createSign("RSA-SHA256");signer.update(unsigned);signer.end();
  const assertion=`${unsigned}.${signer.sign(account.private_key,"base64url")}`;
  const response=await fetch(account.token_uri??"https://oauth2.googleapis.com/token",{method:"POST",headers:{"content-type":"application/x-www-form-urlencoded"},body:new URLSearchParams({grant_type:"urn:ietf:params:oauth:grant-type:jwt-bearer",assertion}),signal:AbortSignal.timeout(5000)});
  if(!response.ok)throw new Error(`Google authentication failed (${response.status})`);
  const body=await response.json() as {access_token?:string};if(!body.access_token)throw new Error("Google authentication returned no access token");return body.access_token;
}

export function buildDraftBoardRequests(db:Database.Database,draftId:string,config:SheetConfig){
  const teams=db.prepare(`SELECT t.id,o.display_name owner FROM teams t JOIN owners o ON o.id=t.owner_id WHERE t.draft_id=?`).all(draftId) as {id:string;owner:string}[];
  const rows=db.prepare(`SELECT rs.team_id teamId,rs.slot_type slotType,rs.ordinal,p.display_name player,s.price FROM roster_slots rs LEFT JOIN players p ON p.id=rs.player_id LEFT JOIN sales s ON s.id=rs.filled_sale_id AND s.voided_event_id IS NULL WHERE rs.team_id IN (SELECT id FROM teams WHERE draft_id=?)`).all(draftId) as {teamId:string;slotType:string;ordinal:number;player:string|null;price:number|null}[];
  const bySlot=new Map(rows.map(row=>[`${row.teamId}:${row.slotType}:${row.ordinal}`,row]));
  return teams.map(team=>{
    const target=config.owners[team.owner];if(!target)throw new Error(`No draft-board mapping for ${team.owner}`);
    const values=SLOT_ORDER.map(key=>{const row=bySlot.get(`${team.id}:${key}`);return {values:[row?.player?{userEnteredValue:{stringValue:row.player}}:{},row?.price!=null?{userEnteredValue:{numberValue:row.price}}:{}] as CellValue[]};});
    return {updateCells:{range:{sheetId:config.sheetId,startRowIndex:target.firstRosterRow,endRowIndex:target.firstRosterRow+SLOT_ORDER.length,startColumnIndex:target.playerColumn,endColumnIndex:target.priceColumn+1},rows:values,fields:"userEnteredValue"}};
  });
}

export function sheetSyncStatus(db:Database.Database,draftId:string){
  const draft=db.prepare("SELECT google_sheets_sync_enabled enabled FROM drafts WHERE id=?").get(draftId) as {enabled:number}|undefined;
  const accountConfigured=Boolean(process.env.GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON||process.env.GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE);
  const counts=db.prepare(`SELECT o.status,COUNT(*) count FROM sync_outbox o JOIN draft_events e ON e.id=o.event_id WHERE o.draft_id=? AND o.destination='google_sheets' AND e.event_type IN ('sale_recorded','sale_voided','roster_slot_reassigned') GROUP BY o.status`).all(draftId) as {status:string;count:number}[];
  const map=Object.fromEntries(counts.map(row=>[row.status,row.count]));
  const failure=db.prepare(`SELECT o.last_error lastError FROM sync_outbox o JOIN draft_events e ON e.id=o.event_id WHERE o.draft_id=? AND o.destination='google_sheets' AND o.status='failed' AND e.event_type IN ('sale_recorded','sale_voided','roster_slot_reassigned') ORDER BY o.updated_at DESC LIMIT 1`).get(draftId) as {lastError:string}|undefined;
  return {configured:accountConfigured,enabled:Boolean(draft?.enabled),pending:(map.pending??0)+(map.in_flight??0),failed:map.failed??0,succeeded:map.succeeded??0,lastError:failure?.lastError??null};
}

export async function syncGoogleSheetsOutbox(db:Database.Database,draftId:string,configPath:string):Promise<void>{
  const enabled=(db.prepare("SELECT google_sheets_sync_enabled enabled FROM drafts WHERE id=?").get(draftId) as {enabled:number}|undefined)?.enabled;
  if(!enabled)return;
  const account=credentials();if(!account)return;
  const work=db.prepare(`SELECT id,event_id eventId FROM sync_outbox WHERE draft_id=? AND destination='google_sheets' AND status IN ('pending','failed') ORDER BY created_at`).all(draftId) as {id:string;eventId:string}[];
  if(!work.length)return;
  const relevant=work.filter(item=>["sale_recorded","sale_voided","roster_slot_reassigned"].includes((db.prepare("SELECT event_type eventType FROM draft_events WHERE id=?").get(item.eventId) as {eventType:string}).eventType));
  const skipped=work.filter(item=>!relevant.includes(item));
  const markSucceeded=db.prepare("UPDATE sync_outbox SET status='succeeded',attempt_count=attempt_count+1,last_error=NULL,updated_at=CURRENT_TIMESTAMP,succeeded_at=CURRENT_TIMESTAMP WHERE id=?");
  db.transaction(()=>{for(const item of skipped)markSucceeded.run(item.id);})();
  if(!relevant.length)return;
  const ids=relevant.map(item=>item.id),placeholders=ids.map(()=>"?").join(",");
  db.prepare(`UPDATE sync_outbox SET status='in_flight',attempt_count=attempt_count+1,updated_at=CURRENT_TIMESTAMP WHERE id IN (${placeholders})`).run(...ids);
  try{
    await syncGoogleSheetsSnapshot(db,draftId,configPath,account);
    db.transaction(()=>{for(const id of ids)markSucceeded.run(id);})();
  }catch(error){
    const message=error instanceof Error?error.message:String(error);
    const fail=db.prepare("UPDATE sync_outbox SET status='failed',last_error=?,next_attempt_at=datetime('now','+30 seconds'),updated_at=CURRENT_TIMESTAMP WHERE id=?");
    db.transaction(()=>{for(const id of ids)fail.run(message,id);})();
  }
}

export async function syncGoogleSheetsSnapshot(db:Database.Database,draftId:string,configPath:string,providedAccount?:ServiceAccount):Promise<void>{
  const enabled=(db.prepare("SELECT google_sheets_sync_enabled enabled FROM drafts WHERE id=?").get(draftId) as {enabled:number}|undefined)?.enabled;
  if(!enabled)return;
  const account=providedAccount??credentials();if(!account)return;
  const config=JSON.parse(readFileSync(configPath,"utf8")) as SheetConfig,token=await accessToken(account),requests=buildDraftBoardRequests(db,draftId,config);
  const response=await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${config.spreadsheetId}:batchUpdate`,{method:"POST",headers:{authorization:`Bearer ${token}`,"content-type":"application/json"},body:JSON.stringify({requests}),signal:AbortSignal.timeout(7000)});
  if(!response.ok){const body=await response.text();throw new Error(`Google Sheets update failed (${response.status}): ${body.slice(0,240)}`);}
}
