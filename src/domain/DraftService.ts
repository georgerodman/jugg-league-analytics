import Database from "better-sqlite3";
import { readFileSync } from "node:fs";
import { randomUUID } from "node:crypto";

export type Position = "QB" | "RB" | "WR" | "TE" | "K" | "DEF";
export type Command = { draftId: string; expectedVersion: number; idempotencyKey: string; occurredAt: string };
export type TeamInput = { id: string; ownerId: string; ownerName: string; name: string };
export type PlayerInput = { id: string; name: string; position: Position; nflTeam?: string; identityStatus: "stable"|"provisional" };
export type SlotTemplate = { slotType: string; count: number; eligiblePositions: Position[] };

export class DomainError extends Error {
  constructor(public readonly code: string, message: string) { super(message); }
}

export class DraftService {
  constructor(readonly db: Database.Database) { this.db.pragma("foreign_keys = ON"); }

  static open(path: string, migrationPath: string): DraftService {
    const db = new Database(path);
    db.pragma("journal_mode = WAL"); db.pragma("synchronous = FULL");
    if (!db.prepare("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'").get())
      db.exec(readFileSync(migrationPath, "utf8"));
    return new DraftService(db);
  }

  initializeDraft(input: { id:string; season:number; name:string; teams:TeamInput[]; players:PlayerInput[]; slots:SlotTemplate[] }): void {
    this.db.transaction(() => {
      this.db.prepare("INSERT INTO drafts(id,season,name,status,team_count,budget_per_team,minimum_bid,required_players_per_team) VALUES(?,?,?,'setup',?,200,1,14)").run(input.id,input.season,input.name,input.teams.length);
      for (const team of input.teams) {
        this.db.prepare("INSERT OR IGNORE INTO owners(id,display_name) VALUES(?,?)").run(team.ownerId,team.ownerName);
        this.db.prepare("INSERT INTO teams(id,draft_id,owner_id,display_name,starting_budget) VALUES(?,?,?,?,200)").run(team.id,input.id,team.ownerId,team.name);
        const slotCount=input.slots.reduce((sum,slot)=>sum+slot.count,0);
        this.db.prepare("INSERT INTO team_draft_state(team_id,remaining_budget,open_slot_count) VALUES(?,200,?)").run(team.id,slotCount);
        for (const slot of input.slots) for(let ordinal=1;ordinal<=slot.count;ordinal++)
          this.db.prepare("INSERT INTO roster_slots(id,team_id,slot_type,ordinal,eligible_positions_json) VALUES(?,?,?,?,?)").run(`${team.id}:${slot.slotType}:${ordinal}`,team.id,slot.slotType,ordinal,JSON.stringify(slot.eligiblePositions));
      }
      for (const player of input.players) {
        this.db.prepare("INSERT INTO players(id,display_name,position,nfl_team,identity_status) VALUES(?,?,?,?,?)").run(player.id,player.name,player.position,player.nflTeam ?? null,player.identityStatus);
        this.db.prepare("INSERT INTO draft_player_pool(draft_id,player_id) VALUES(?,?)").run(input.id,player.id);
      }
    })();
  }

  startDraft(command: Command): unknown { return this.eventOnly(command,"draft_started","draft",command.draftId,{},()=>this.db.prepare("UPDATE drafts SET status='active' WHERE id=?").run(command.draftId)); }

  openNomination(command: Command & { playerId:string; nominatedByTeamId?:string }): unknown {
    return this.execute(command,"nomination_opened","nomination",command.playerId,{playerId:command.playerId,nominatedByTeamId:command.nominatedByTeamId ?? null},eventId=>{
      const pool=this.db.prepare("SELECT status FROM draft_player_pool WHERE draft_id=? AND player_id=?").get(command.draftId,command.playerId) as {status:string}|undefined;
      if (!pool) throw new DomainError("PLAYER_NOT_IN_POOL","Player is not in this draft");
      if (pool.status!=="available") throw new DomainError("PLAYER_UNAVAILABLE","Player is not available");
      const nominationId=randomUUID();
      this.db.prepare("INSERT INTO nominations(id,draft_id,player_id,nominated_by_team_id,status,opened_event_id,opened_at) VALUES(?,?,?,?,'open',?,?)").run(nominationId,command.draftId,command.playerId,command.nominatedByTeamId ?? null,eventId,command.occurredAt);
      this.db.prepare("UPDATE draft_player_pool SET status='nominated' WHERE draft_id=? AND player_id=?").run(command.draftId,command.playerId);
      return {nominationId};
    });
  }

  cancelNomination(command: Command): unknown {
    return this.execute(command,"nomination_cancelled","nomination",command.draftId,{},eventId=>{
      const nomination=this.openNominationRow(command.draftId);
      this.db.prepare("UPDATE nominations SET status='cancelled',closed_event_id=?,closed_at=? WHERE id=?").run(eventId,command.occurredAt,nomination.id);
      this.db.prepare("UPDATE draft_player_pool SET status='available' WHERE draft_id=? AND player_id=?").run(command.draftId,nomination.player_id);
      return {nominationId:nomination.id};
    });
  }

  recordSale(command: Command & { winnerTeamId:string; price:number }): unknown {
    return this.execute(command,"sale_recorded","sale",command.draftId,{winnerTeamId:command.winnerTeamId,price:command.price},eventId=>{
      const nomination=this.openNominationRow(command.draftId);
      const draft=this.db.prepare("SELECT minimum_bid FROM drafts WHERE id=?").get(command.draftId) as {minimum_bid:number};
      const team=this.db.prepare("SELECT s.remaining_budget,s.open_slot_count,p.position FROM team_draft_state s JOIN teams t ON t.id=s.team_id JOIN players p ON p.id=? WHERE s.team_id=? AND t.draft_id=?").get(nomination.player_id,command.winnerTeamId,command.draftId) as {remaining_budget:number;open_slot_count:number;position:Position}|undefined;
      if (!team) throw new DomainError("TEAM_NOT_IN_DRAFT","Winner is not in this draft");
      if (!Number.isInteger(command.price)||command.price<draft.minimum_bid) throw new DomainError("INVALID_PRICE","Sale price is below the minimum bid");
      const maximum=team.remaining_budget-(team.open_slot_count-1)*draft.minimum_bid;
      if (command.price>maximum) throw new DomainError("BUDGET_RESERVE","Sale would prevent filling remaining slots");
      const slots=this.db.prepare("SELECT id,slot_type,eligible_positions_json FROM roster_slots WHERE team_id=? AND player_id IS NULL").all(command.winnerTeamId) as {id:string;slot_type:string;eligible_positions_json:string}[];
      const slot=slots.filter(row=>(JSON.parse(row.eligible_positions_json) as Position[]).includes(team.position)).sort((a,b)=>(a.slot_type==="BN"?1:0)-(b.slot_type==="BN"?1:0))[0];
      if (!slot) throw new DomainError("NO_ELIGIBLE_SLOT","No eligible roster slot remains");
      const saleId=randomUUID();
      this.db.prepare("UPDATE nominations SET status='sold',closed_event_id=?,closed_at=? WHERE id=?").run(eventId,command.occurredAt,nomination.id);
      this.db.prepare("INSERT INTO sales(id,draft_id,nomination_id,player_id,winner_team_id,price,recorded_event_id,roster_slot_id,recorded_at) VALUES(?,?,?,?,?,?,?,?,?)").run(saleId,command.draftId,nomination.id,nomination.player_id,command.winnerTeamId,command.price,eventId,slot.id,command.occurredAt);
      this.db.prepare("UPDATE roster_slots SET player_id=?,filled_sale_id=? WHERE id=?").run(nomination.player_id,saleId,slot.id);
      this.db.prepare("UPDATE draft_player_pool SET status='sold' WHERE draft_id=? AND player_id=?").run(command.draftId,nomination.player_id);
      this.db.prepare("UPDATE team_draft_state SET remaining_budget=remaining_budget-?,open_slot_count=open_slot_count-1,rostered_player_count=rostered_player_count+1,version=version+1,updated_at=? WHERE team_id=?").run(command.price,command.occurredAt,command.winnerTeamId);
      return {saleId,rosterSlotId:slot.id};
    });
  }

  voidSale(command: Command & { saleId:string }): unknown {
    return this.execute(command,"sale_voided","sale",command.saleId,{saleId:command.saleId},eventId=>{
      const sale=this.db.prepare("SELECT * FROM sales WHERE id=? AND draft_id=? AND voided_event_id IS NULL").get(command.saleId,command.draftId) as any;
      if (!sale) throw new DomainError("ACTIVE_SALE_NOT_FOUND","Active sale was not found");
      this.db.prepare("UPDATE sales SET voided_event_id=?,voided_at=? WHERE id=?").run(eventId,command.occurredAt,sale.id);
      this.db.prepare("UPDATE roster_slots SET player_id=NULL,filled_sale_id=NULL WHERE id=? AND filled_sale_id=?").run(sale.roster_slot_id,sale.id);
      this.db.prepare("UPDATE draft_player_pool SET status='available' WHERE draft_id=? AND player_id=?").run(command.draftId,sale.player_id);
      this.db.prepare("UPDATE team_draft_state SET remaining_budget=remaining_budget+?,open_slot_count=open_slot_count+1,rostered_player_count=rostered_player_count-1,version=version+1,updated_at=? WHERE team_id=?").run(sale.price,command.occurredAt,sale.winner_team_id);
      return {saleId:sale.id};
    });
  }

  recoveryAudit(draftId:string): string[] {
    const issues:string[]=[];
    const draft=this.db.prepare("SELECT state_version FROM drafts WHERE id=?").get(draftId) as {state_version:number}|undefined;
    if (!draft) return ["draft_missing"];
    const event=this.db.prepare("SELECT COALESCE(MAX(sequence),0) sequence FROM draft_events WHERE draft_id=?").get(draftId) as {sequence:number};
    if (draft.state_version!==event.sequence) issues.push("event_version_mismatch");
    const teams=this.db.prepare("SELECT t.id,t.starting_budget,s.remaining_budget,s.open_slot_count,s.rostered_player_count FROM teams t JOIN team_draft_state s ON s.team_id=t.id WHERE t.draft_id=?").all(draftId) as any[];
    for (const team of teams) {
      const sales=this.db.prepare("SELECT COALESCE(SUM(price),0) spend,COUNT(*) count FROM sales WHERE draft_id=? AND winner_team_id=? AND voided_event_id IS NULL").get(draftId,team.id) as any;
      if (team.remaining_budget!==team.starting_budget-sales.spend) issues.push(`budget_mismatch:${team.id}`);
      if (team.rostered_player_count!==sales.count) issues.push(`roster_count_mismatch:${team.id}`);
      if (team.open_slot_count+team.rostered_player_count!==14) issues.push(`slot_count_mismatch:${team.id}`);
    }
    return issues;
  }

  private openNominationRow(draftId:string): any {
    const row=this.db.prepare("SELECT * FROM nominations WHERE draft_id=? AND status='open'").get(draftId);
    if (!row) throw new DomainError("NO_OPEN_NOMINATION","There is no open nomination"); return row;
  }
  private eventOnly(command:Command,type:string,aggregateType:string,aggregateId:string,payload:unknown,apply:()=>void):unknown { return this.execute(command,type,aggregateType,aggregateId,payload,()=>{apply();return {};}); }
  private execute(command:Command,eventType:string,aggregateType:string,aggregateId:string,payload:unknown,apply:(eventId:string)=>unknown):unknown {
    return this.db.transaction(()=>{
      const prior=this.db.prepare("SELECT id,payload_json FROM draft_events WHERE draft_id=? AND idempotency_key=?").get(command.draftId,command.idempotencyKey) as any;
      if (prior) return {eventId:prior.id,replayed:true};
      const draft=this.db.prepare("SELECT state_version,status FROM drafts WHERE id=?").get(command.draftId) as {state_version:number;status:string}|undefined;
      if (!draft) throw new DomainError("DRAFT_NOT_FOUND","Draft was not found");
      if (draft.state_version!==command.expectedVersion) throw new DomainError("VERSION_CONFLICT",`Expected ${command.expectedVersion}, found ${draft.state_version}`);
      if (eventType!=="draft_started"&&draft.status!=="active") throw new DomainError("DRAFT_NOT_ACTIVE","Draft is not active");
      const eventId=randomUUID(), sequence=draft.state_version+1;
      this.db.prepare("INSERT INTO draft_events(id,draft_id,sequence,event_type,aggregate_type,aggregate_id,idempotency_key,payload_json,occurred_at) VALUES(?,?,?,?,?,?,?,?,?)").run(eventId,command.draftId,sequence,eventType,aggregateType,aggregateId,command.idempotencyKey,JSON.stringify(payload),command.occurredAt);
      const result=apply(eventId);
      this.db.prepare("UPDATE drafts SET state_version=?,updated_at=? WHERE id=?").run(sequence,command.occurredAt,command.draftId);
      this.db.prepare("INSERT INTO sync_outbox(id,draft_id,event_id,destination,operation_key,payload_json) VALUES(?,? ,?,'google_sheets',?,?)").run(randomUUID(),command.draftId,eventId,`${command.draftId}:${eventId}`,JSON.stringify({eventType,eventId,sequence}));
      return {eventId,sequence,replayed:false,...(result as object)};
    })();
  }
}
