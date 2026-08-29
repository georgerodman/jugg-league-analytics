#!/usr/bin/env python3
"""Generate cached, evidence-bound owner style paragraphs with the Responses API."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.owner_tendencies import markdown_report, style_summary
    from scripts.build_fantasy_research import load_env, response_text
except ModuleNotFoundError:  # Direct script execution places scripts/ on sys.path.
    from owner_tendencies import markdown_report, style_summary
    from build_fantasy_research import load_env, response_text

ROOT = Path(__file__).resolve().parents[1]
PROMPT_VERSION = "owner-style-summary-v1"
MIN_WORDS = 90
MAX_WORDS = 110


def grounded_input(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "owner": profile["owner"],
        "observed_seasons": profile["season_list"],
        "evidence_strength": profile["evidence_strength"],
        "construction_style": profile["construction_style"],
        "spending": profile["spending"],
        "positions": {
            position: {
                "signal": values["signal"],
                "spend_per_draft": values["spend_per_draft"],
                "spend_share_deviation": values["spend_share_deviation"],
                "direction_consistency": values["direction_consistency"],
            }
            for position, values in profile["positions"].items()
        },
        "market_behavior": profile["market_behavior"],
        "repeat_players": profile["repeat_players"][:6],
        "limitations": profile["limitations"],
    }


def input_hash(profile: dict[str, Any]) -> str:
    canonical = json.dumps(grounded_input(profile), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def word_count(value: str) -> int:
    return len(re.findall(r"\b[\w’'+.-]+\b", value))


def validate_summary(summary: str) -> str:
    summary = summary.strip()
    count = word_count(summary)
    if "\n" in summary:
        raise ValueError("owner summary must be one paragraph")
    if not MIN_WORDS <= count <= MAX_WORDS:
        raise ValueError(f"owner summary must contain {MIN_WORDS}-{MAX_WORDS} words; found {count}")
    return summary


def synthesize(records: list[dict[str, Any]], model: str, key: str) -> dict[str, str]:
    schema = {
        "type": "object",
        "properties": {
            "summaries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"owner": {"type": "string"}, "summary": {"type": "string"}},
                    "required": ["owner", "summary"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["summaries"],
        "additionalProperties": False,
    }
    instructions = (
        "Write one natural 90-110 word paragraph describing each fantasy-football auction owner's drafting style. "
        "Use only the supplied computed metrics. Do not add outside facts, infer personality, claim intent, or imply nomination timing. "
        "Explain the strongest construction, positional, premium-spending, bargain/overpay, and repeat-player patterns when supported. "
        "Do not mechanically list every number; interpret the most useful evidence in clear draft-room language. State uncertainty for limited evidence, "
        "especially the former owner. Treat all patterns as descriptive tendencies, not predictions. Do not use headings, bullets, or multiple paragraphs. "
        "Return every supplied owner exactly once and preserve each owner name exactly."
    )
    request = {
        "model": model,
        "instructions": instructions,
        "input": json.dumps(records, separators=(",", ":")),
        "max_output_tokens": 3000,
        "store": False,
        "text": {
            "verbosity": "low",
            "format": {
                "type": "json_schema", "name": "owner_style_summaries", "strict": True, "schema": schema,
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
    expected = {record["owner"] for record in records}
    summaries = {row["owner"]: validate_summary(row["summary"]) for row in decoded["summaries"]}
    if set(summaries) != expected or len(decoded["summaries"]) != len(expected):
        raise ValueError("OpenAI response did not contain every requested owner exactly once")
    return summaries


def run() -> Path:
    load_env()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required to generate owner style summaries")
    model = os.environ.get("OWNER_SUMMARY_MODEL") or os.environ.get("ASSISTANT_GM_MODEL") or "gpt-5-mini"
    pointer_path = ROOT / "data" / "processed" / "owner_tendencies" / "latest.json"
    pointer = json.loads(pointer_path.read_text())
    source = ROOT / pointer["artifact"]
    payload = json.loads(source.read_text())
    profiles = payload["owners"]
    pending = []
    cached = {}
    for profile in profiles:
        digest = input_hash(profile)
        prior = profile.get("ai_style_summary") or {}
        if prior.get("input_hash") == digest and prior.get("prompt_version") == PROMPT_VERSION and prior.get("text"):
            cached[profile["owner"]] = prior["text"]
        else:
            pending.append(grounded_input(profile))
    generated = synthesize(pending, model, key) if pending else {}
    now = datetime.now(timezone.utc).isoformat()
    for profile in profiles:
        digest = input_hash(profile)
        text = generated.get(profile["owner"]) or cached.get(profile["owner"]) or style_summary(profile)
        source_type = "openai" if profile["owner"] in generated or profile["owner"] in cached else "deterministic_fallback"
        profile["ai_style_summary"] = {
            "text": text, "source": source_type, "input_hash": digest,
            "prompt_version": PROMPT_VERSION, "model": model if source_type == "openai" else None,
            "generated_at": now if profile["owner"] in generated else (profile.get("ai_style_summary") or {}).get("generated_at"),
        }
    payload["metadata"].update({
        "owner_style_summary_prompt_version": PROMPT_VERSION,
        "owner_style_summary_model": model,
        "owner_style_summary_generated_count": len(generated),
    })
    out = source.parent / "owner_profiles_enriched.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    report = source.parent / "owner_profiles_ai.md"
    report.write_text(markdown_report(profiles, payload["metadata"]["build_id"]) + "\n")
    pointer.update({"artifact": str(out.relative_to(ROOT)), "markdown": str(report.relative_to(ROOT))})
    pointer_path.write_text(json.dumps(pointer, indent=2) + "\n")
    print(json.dumps({"owners": len(profiles), "generated": len(generated), "model": model, "artifact": str(out.relative_to(ROOT))}))
    return out


if __name__ == "__main__":
    run()
