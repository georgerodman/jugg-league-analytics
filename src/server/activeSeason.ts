import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { z } from "zod";

export const activeSeasonSchema=z.object({
  schemaVersion:z.literal(1),
  season:z.number().int().min(2020).max(2100),
  draftId:z.string().regex(/^jugg-\d{4}$/),
  draftName:z.string().min(1),
  databasePath:z.string().min(1),
  googleSheetsConfigPath:z.string().min(1),
}).superRefine((value,context)=>{
  if(value.draftId!==`jugg-${value.season}`)context.addIssue({code:"custom",path:["draftId"],message:"draftId must match the configured season"});
  if(!value.databasePath.startsWith(".local/"))context.addIssue({code:"custom",path:["databasePath"],message:"databasePath must remain under .local/"});
  if(!value.googleSheetsConfigPath.startsWith("config/"))context.addIssue({code:"custom",path:["googleSheetsConfigPath"],message:"Google Sheets configuration must remain under config/"});
});

const root=process.cwd();
export const activeSeason=activeSeasonSchema.parse(JSON.parse(readFileSync(resolve(root,"config/active-season.json"),"utf8")));
export const activeSeasonPaths={
  database:resolve(root,activeSeason.databasePath),
  googleSheets:resolve(root,activeSeason.googleSheetsConfigPath),
  canonicalProjections:`data/processed/canonical_projections/${activeSeason.season}/latest.json`,
  fantasyProsAdp:`data/processed/fantasypros_adp/${activeSeason.season}/latest.json`,
  espnSalaryCapValues:`data/processed/espn_salary_cap_values/${activeSeason.season}/latest.json`,
  nflverseDepthCharts:`data/processed/nflverse_depth_charts/${activeSeason.season}/latest.json`,
  fantasyProsContext:`data/processed/fantasypros_context/${activeSeason.season}/latest.json`,
};
