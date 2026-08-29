#!/usr/bin/env python3
"""Repair scoring-format narration in the latest completed research artifact."""

import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import build_fantasy_research as research

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = re.compile(r"\b(?:half[- ]?)?PPR\b", re.IGNORECASE)


def sanitized(text):
    text = re.sub(r"half[- ]?PPR", "reception-weighted", text, flags=re.IGNORECASE)
    text = re.sub(r"non-PPR", "standard", text, flags=re.IGNORECASE)
    return re.sub(r"PPR", "reception-weighted", text, flags=re.IGNORECASE)


def response_text(payload):
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    return "".join(
        item.get("text", "")
        for output in payload.get("output", [])
        for item in output.get("content", [])
        if item.get("type") in ("output_text", "text")
    )


def main():
    research.load_env()
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required")
    model = os.environ.get("FANTASY_RESEARCH_MODEL") or os.environ.get("ASSISTANT_GM_MODEL") or "gpt-5-mini"
    pointer_path = ROOT / "data/processed/fantasy_research/latest.json"
    pointer = json.loads(pointer_path.read_text())
    artifact_path = ROOT / pointer["artifact"]
    artifact = json.loads(artifact_path.read_text())
    affected = [
        row for row in artifact["summaries"]
        if FORBIDDEN.search(row.get("card_summary", "")) or FORBIDDEN.search(row.get("full_writeup", ""))
    ]
    schema = {
        "type": "object",
        "properties": {
            "summaries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "player_id": {"type": "string"},
                        "card_summary": {"type": "string"},
                        "full_writeup": {"type": "string"},
                    },
                    "required": ["player_id", "card_summary", "full_writeup"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["summaries"],
        "additionalProperties": False,
    }
    repaired = {}
    for start in range(0, len(affected), 5):
        batch = affected[start:start + 5]
        request = {
            "model": model,
            "instructions": (
                "Copyedit the supplied card summary and full writeup while preserving every football conclusion, fact, price, rank, date, and paragraph structure. "
                "Remove all explicit discussion or naming of scoring formats and state the resulting football implications directly. "
                "Never introduce new facts, analysis, attribution, or meta-commentary. Never output the forbidden three-letter scoring acronym present in the input."
            ),
            "input": json.dumps([
                {"player_id": row["player_id"], "card_summary": sanitized(row["card_summary"]), "full_writeup": sanitized(row["full_writeup"])}
                for row in batch
            ]),
            "max_output_tokens": 5000,
            "store": False,
            "text": {"verbosity": "low", "format": {"type": "json_schema", "name": "repaired_summaries", "strict": True, "schema": schema}},
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(request).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            decoded = json.loads(response_text(json.loads(response.read())))
        expected = {row["player_id"] for row in batch}
        returned = {row["player_id"] for row in decoded["summaries"]}
        if returned != expected:
            raise RuntimeError(f"Repair response IDs differed: expected {expected}, returned {returned}")
        for row in decoded["summaries"]:
            if FORBIDDEN.search(row["card_summary"]) or FORBIDDEN.search(row["full_writeup"]):
                raise RuntimeError(f"Forbidden format language remained for {row['player_id']}")
            repaired[row["player_id"]] = row
        print(f"Language repair: {min(start + 5, len(affected))}/{len(affected)}", flush=True)
    for row in artifact["summaries"]:
        replacement = repaired.get(row["player_id"])
        if replacement:
            row["card_summary"] = replacement["card_summary"].strip()
            row["full_writeup"] = replacement["full_writeup"].strip()
    artifact["metadata"]["language_repair_at"] = datetime.now(timezone.utc).isoformat()
    artifact["metadata"]["language_repair_count"] = len(repaired)
    artifact_path.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps({"repaired_players": len(repaired), "artifact": pointer["artifact"]}))


if __name__ == "__main__":
    main()
