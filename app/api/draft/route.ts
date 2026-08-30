import { NextResponse } from "next/server";
import { applyDraftAction, readDraftRoom, toApiError } from "../../../src/server/draftStore";
import { draftRuntime, finalizeDraftRoom, getDraftService, resetDraftRoom } from "../../../src/server/draftStore";
import { syncGoogleSheetsOutbox, syncGoogleSheetsSnapshot } from "../../../src/server/googleSheetsSync";

export const runtime="nodejs";
export const dynamic="force-dynamic";

export async function GET(){try{return NextResponse.json(readDraftRoom());}catch(error){const api=toApiError(error);return NextResponse.json(api.body,{status:api.status});}}
export async function POST(request:Request){try{const action=await request.json();const configPath=draftRuntime.googleSheetsConfigPath;if(action.type==="finalizeDraft"){if(action.confirmation!=="FINALIZE")return NextResponse.json({error:"FINALIZE_NOT_CONFIRMED",message:"Type FINALIZE to confirm."},{status:400});const result=await finalizeDraftRoom();return NextResponse.json(result.view);}if(action.type==="resetDraft"){if(action.confirmation!=="RESET")return NextResponse.json({error:"RESET_NOT_CONFIRMED",message:"Type RESET to confirm."},{status:400});resetDraftRoom({preservePreferences:action.preservePreferences!==false});void syncGoogleSheetsSnapshot(getDraftService().db,draftRuntime.draftId,configPath).catch(console.error);return NextResponse.json(readDraftRoom());}if(action.type!=="retrySync")applyDraftAction(action);if(action.type==="sale"||action.type==="voidSale"||action.type==="reassignRosterSlot"||action.type==="retrySync")void syncGoogleSheetsOutbox(getDraftService().db,draftRuntime.draftId,configPath).catch(console.error);return NextResponse.json(readDraftRoom());}catch(error){const api=toApiError(error);return NextResponse.json(api.body,{status:api.status});}}
