#!/usr/bin/env python3
"""Generate only concise Pros/Cons fields for cached fantasy writeups."""

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import build_fantasy_research as research

ROOT = Path(__file__).resolve().parents[1]
PROMPT_VERSION = "fantasy-pros-cons-v1"
CHECKPOINT = ROOT / "data/processed/fantasy_research/pros_cons_checkpoint.json"


def response_text(payload):
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    return "".join(
        item.get("text", "")
        for output in payload.get("output", [])
        for item in output.get("content", [])
        if item.get("type") in ("output_text", "text")
    )


def synthesize(records, model, key, results):
    schema = {
        "type": "object",
        "properties": {
            "summaries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "player_id": {"type": "string"},
                        "pros_summary": {"type": "string"},
                        "cons_summary": {"type": "string"},
                    },
                    "required": ["player_id", "pros_summary", "cons_summary"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["summaries"],
        "additionalProperties": False,
    }
    instructions = (
        "Create only concise Pros and Cons for each fantasy-football player; do not rewrite the supplied card summary or full writeup. "
        "PROS SUMMARY: exactly one natural sentence of at most 24 words containing the two or three strongest distinct favorable points. "
        "CONS SUMMARY: exactly one natural sentence of at most 24 words containing the two or three most important risks, weaknesses, or price conditions. "
        "Prefer compact comma-separated football phrases, such as 'Elite workload, strong offensive line, and receiving growth.' "
        "Synthesize across the supplied material without naming analysts or publications, mentioning evidence or sources, or adding outside facts. "
        "Avoid repeating the player name and avoid labels such as Pros, Cons, Why, or Risk because the interface supplies them."
    )
    for start in range(0, len(records), 10):
        batch = records[start : start + 10]
        request = {
            "model": model,
            "instructions": instructions,
            "input": json.dumps(batch),
            "max_output_tokens": 2500,
            "store": False,
            "text": {
                "verbosity": "low",
                "format": {
                    "type": "json_schema",
                    "name": "player_pros_cons",
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(request).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        parsed = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    parsed = json.loads(response.read())
                break
            except urllib.error.HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                    raise
                time.sleep(2 ** (attempt + 1))
        if parsed is None:
            raise RuntimeError("OpenAI response was unavailable after retries")
        decoded = json.loads(response_text(parsed))
        for row in decoded["summaries"]:
            pros = row["pros_summary"].strip()
            cons = row["cons_summary"].strip()
            if len(pros.split()) > 24 or len(cons.split()) > 24 or "\n" in pros or "\n" in cons:
                raise RuntimeError(f"Pros/Cons length validation failed for {row['player_id']}")
            results[row["player_id"]] = {"pros_summary": pros, "cons_summary": cons}
        CHECKPOINT.write_text(json.dumps({"prompt_version": PROMPT_VERSION, "results": results}, indent=2) + "\n")
        print(f"AI Pros/Cons: {min(start + 10, len(records))}/{len(records)}", flush=True)
        time.sleep(0.15)
    return results


def main():
    research.load_env()
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required to generate Pros/Cons summaries")
    model = os.environ.get("FANTASY_RESEARCH_MODEL") or os.environ.get("ASSISTANT_GM_MODEL") or "gpt-5-mini"
    pointer_path = ROOT / "data/processed/fantasy_research/latest.json"
    pointer = json.loads(pointer_path.read_text())
    source_path = ROOT / pointer["artifact"]
    artifact = json.loads(source_path.read_text())

    grouped, _ = research.evidence()
    profiles, targets, team_targets, handcuffs, fantasypros, format_notes, auction = research.contextual_evidence()
    inputs = {
        player_id: research.input_record(player_id, rows, profiles, targets, team_targets, handcuffs, fantasypros, format_notes, auction)
        for player_id, rows in grouped.items()
    }
    checkpoint_results = {}
    if CHECKPOINT.exists():
        checkpoint = json.loads(CHECKPOINT.read_text())
        if checkpoint.get("prompt_version") == PROMPT_VERSION:
            checkpoint_results = checkpoint.get("results", {})
    pending = []
    for row in artifact["summaries"]:
        record = inputs.get(row["player_id"])
        if not record:
            continue
        if row.get("pros_summary") and row.get("cons_summary") and row.get("pros_cons_input_hash") == record["input_hash"] and row.get("pros_cons_prompt_version") == PROMPT_VERSION:
            continue
        if row["player_id"] in checkpoint_results:
            continue
        pending.append({
            "player_id": row["player_id"],
            "player_name": row["player_name"],
            "card_summary": row["card_summary"],
            "full_writeup": row["full_writeup"],
            "opinions": record["evidence"],
            "context": record["context"],
        })
    generated = synthesize(pending, model, key, checkpoint_results) if pending else checkpoint_results
    now = datetime.now(timezone.utc).isoformat()
    before = {row["player_id"]: (row["card_summary"], row["full_writeup"]) for row in artifact["summaries"]}
    for row in artifact["summaries"]:
        result = generated.get(row["player_id"])
        if not result:
            continue
        row.update(result)
        row["pros_cons_input_hash"] = row["input_hash"]
        row["pros_cons_prompt_version"] = PROMPT_VERSION
        row["pros_cons_model"] = model
        row["pros_cons_generated_at"] = now
    after = {row["player_id"]: (row["card_summary"], row["full_writeup"]) for row in artifact["summaries"]}
    if before != after:
        raise RuntimeError("Card or full writeups changed during Pros/Cons enrichment")

    build_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = ROOT / "data/processed/fantasy_research" / build_id
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact["metadata"] = {
        **artifact["metadata"],
        "schema_version": 3,
        "build_id": build_id,
        "built_at": now,
        "pros_cons_prompt_version": PROMPT_VERSION,
        "pros_cons_model": model,
    }
    output_path = output_dir / "player_summaries.json"
    output_path.write_text(json.dumps(artifact, indent=2) + "\n")
    pointer_path.write_text(json.dumps({**pointer, "schema_version": 3, "artifact": str(output_path.relative_to(ROOT))}, indent=2) + "\n")
    if CHECKPOINT.exists():
        CHECKPOINT.unlink()
    print(json.dumps({"players": len(artifact["summaries"]), "pros_cons_generated": len(generated), "card_and_full_writeups_changed": 0}))


if __name__ == "__main__":
    main()
