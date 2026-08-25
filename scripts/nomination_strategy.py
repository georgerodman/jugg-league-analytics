#!/usr/bin/env python3
"""Pure nomination-intent recommendations; intentionally not wired to the UI."""

from __future__ import annotations

from typing import Any


def recommend_nominations(candidates: list[dict[str, Any]], limit_per_intent: int = 3) -> dict[str, list[dict[str, Any]]]:
    """Rank nomination options from a live-state scenario prepared by the draft model."""
    buckets = {intent: [] for intent in ("acquire", "bargain_test", "budget_drain", "information", "hold")}
    for row in candidates:
        demand = float(row.get("likely_bidder_count", 0)); price = float(row.get("expected_price", 0)); low = float(row.get("price_low", price))
        equity = float(row.get("championship_equity_delta", 0)); preference = float(row.get("preference_adjustment", 0))
        accidental = float(row.get("accidental_win_risk", 0)); opponent_pressure = float(row.get("opponent_budget_pressure", 0))
        alternatives = int(row.get("close_alternative_count", 0)); uncertainty = float(row.get("demand_uncertainty", 0))
        scores = {
            "acquire": 8 * equity + preference + max(0, price-low) - 2*accidental,
            "bargain_test": 5 * equity + max(0, price-low) + (3-demand) - accidental,
            "budget_drain": 2*demand + opponent_pressure + price/20 - 4*accidental - max(0, equity),
            "information": 3*uncertainty + demand + alternatives - accidental,
            "hold": 2*equity + preference + max(0, 3-demand) + alternatives - uncertainty,
        }
        intent = max(scores, key=scores.get)
        reason = {
            "acquire": "Improves attainable Renegades roster paths at a tolerable likely price.",
            "bargain_test": "Room demand may be soft enough to create a credible cheap win.",
            "budget_drain": "Likely to consume opponents' budget while preserving stronger Renegades alternatives.",
            "information": "Early demand should reveal useful positional and owner price information.",
            "hold": "Strategic value is more likely preserved by nominating this player later.",
        }[intent]
        buckets[intent].append({**row, "nomination_intent": intent, "nomination_score": round(scores[intent], 3), "reason": reason})
    for intent in buckets:
        buckets[intent] = sorted(buckets[intent], key=lambda row: (-row["nomination_score"], row["player_name"]))[:limit_per_intent]
    return buckets
