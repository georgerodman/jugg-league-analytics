import { z } from "zod";

export const ASSISTANT_CONTEXT_VERSION="assistant-gm-context.v1" as const;
export const ASSISTANT_PROMPT_VERSION="assistant-gm-prompt.v1" as const;
export const triggerSchema=z.enum(["initial","selection","official_nomination","sale","correction","user_question"]);
export const conversationTurnSchema=z.object({role:z.enum(["user","assistant"]),text:z.string().min(1).max(600)}).strict();
const money=z.number().int().nonnegative();
const playerRef=z.object({id:z.string().min(1),name:z.string().min(1),position:z.string().min(1),nflTeam:z.string().nullable(),byeWeek:z.number().int().nullable()});

export const assistantContextSchema=z.object({
  schemaVersion:z.literal(ASSISTANT_CONTEXT_VERSION),draftId:z.string().min(1),stateVersion:z.number().int().nonnegative(),trigger:triggerSchema,
  generatedAt:z.string().datetime(),focus:z.object({player:playerRef,adp:z.number().nullable(),riskFlags:z.array(z.string()),freshness:z.object({label:z.string(),provenance:z.array(z.string())}),prices:z.object({currency:z.literal("USD"),preDraftExpected:money.nullable(),liveExpected:money.nullable(),modeledLow:money.nullable(),modeledHigh:money.nullable(),roomMovement:money.nullable()}),priceBands:z.array(z.object({label:z.enum(["Great","Good","Neutral","Poor","Bad"]),from:money,to:money.nullable()})).length(5).nullable(),walkAway:money.nullable(),production:z.object({projectedPoints:z.number(),xpar:z.number().nullable(),label:z.string(),scarcity:z.string(),fallback:z.string().nullable()}),recommendation:z.object({band:z.string(),scenarioSupport:z.string(),rationale:z.string(),shadowModel:z.literal(true),shadowStatus:z.string()})}).nullable(),
  renegades:z.object({roster:z.array(playerRef),needs:z.array(z.string()),remainingBudget:money,openSlots:z.number().int().nonnegative(),maximumLegalBid:money}).nullable(),
  leagueTeams:z.array(z.object({teamId:z.string(),team:z.string(),owner:z.string(),roster:z.array(playerRef),needs:z.array(z.string()),remainingBudget:money,openSlots:z.number().int().nonnegative(),maximumLegalBid:money})),
  alternatives:z.array(z.object({player:playerRef,liveExpected:money.nullable(),walkAway:money.nullable(),costOfWaiting:z.string()})),
  competitors:z.array(z.object({owner:z.string(),maximumLegalBid:money,rosterFit:z.string(),tendency:z.string().nullable(),uncertainty:z.string()})),
  nominationContext:z.object({isRenegadesTurn:z.boolean(),nextNominator:z.string().nullable()}),
  upcomingTargets:z.array(z.object({player:playerRef,targetPrice:money,walkAway:money,fallback:z.string().nullable(),conditionalPlan:z.string()})),
  recentSales:z.array(z.object({player:z.string(),team:z.string(),price:money})),market:z.object({salesCount:z.number().int().nonnegative(),pressure:z.string()}),whatChanged:z.object({headline:z.string(),reasons:z.array(z.string())}).nullable(),
  leagueOutlook:z.object({rank:z.number().int().positive(),rankRange:z.string(),shadowStatus:z.string()}).nullable(),
  preferences:z.object({structuredAdjustments:z.array(z.string()),untrustedNotes:z.array(z.string()),bounded:z.literal(true)}),missingOrStale:z.array(z.string()),userQuestion:z.string().max(1000).nullable(),conversationHistory:z.array(conversationTurnSchema).max(8),userInputs:z.object({hypotheticalPrices:z.array(money).max(10),authoritative:z.literal(false)})
}).strict();
export type AssistantContext=z.infer<typeof assistantContextSchema>;

export const assistantResponseSchema=z.object({text:z.string().min(1).max(5000),referencedPacketFields:z.array(z.string()).min(1),stateVersion:z.number().int().nonnegative(),promptVersion:z.literal(ASSISTANT_PROMPT_VERSION),uncertaintyFlags:z.array(z.string()),grounding:z.object({valid:z.boolean(),issues:z.array(z.string())})}).strict();
export type AssistantResponse=z.infer<typeof assistantResponseSchema>;
