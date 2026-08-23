import { NextResponse } from "next/server";
import { applyDraftAction, readDraftRoom, toApiError } from "../../../src/server/draftStore";
import { draftRuntime, getDraftService, resetDraftRoom } from "../../../src/server/draftStore";
import { syncGoogleSheetsOutbox, syncGoogleSheetsSnapshot } from "../../../src/server/googleSheetsSync";
import { join } from "node:path";

export const runtime="nodejs";
export const dynamic="force-dynamic";

export async function GET(){try{return NextResponse.json(readDraftRoom());}catch(error){const api=toApiError(error);return NextResponse.json(api.body,{status:api.status});}}
export async function POST(request:Request){try{const action=await request.json();const configPath=join(draftRuntime.root,"config/google_sheets.json");if(action.type==="resetDraft"){if(action.confirmation!=="RESET")return NextResponse.json({error:"RESET_NOT_CONFIRMED",message:"Type RESET to confirm."},{status:400});resetDraftRoom({preservePreferences:action.preservePreferences!==false});void syncGoogleSheetsSnapshot(getDraftService().db,draftRuntime.draftId,configPath).catch(console.error);return NextResponse.json(readDraftRoom());}if(action.type!=="retrySync")applyDraftAction(action);if(action.type==="sale"||action.type==="voidSale"||action.type==="retrySync")void syncGoogleSheetsOutbox(getDraftService().db,draftRuntime.draftId,configPath).catch(console.error);return NextResponse.json(readDraftRoom());}catch(error){const api=toApiError(error);return NextResponse.json(api.body,{status:api.status});}}
