#!/usr/bin/env python3
"""Build auction modeling data and neutral historical model comparisons."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEASONS = tuple(range(2020, 2026))
POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")
MODEL_FEATURES = {
    "position_only": (),
    "espn_adp_only": ("adp_espn",),
    "yahoo_adp_only": ("adp_yahoo",),
    "adp_only": ("adp_espn", "adp_yahoo"),
    "projection_only": ("projected_points_jugg",),
    "prior_price_only": ("prior_jugg_salary",),
    "market_without_espn_value": ("adp_espn", "adp_yahoo", "projected_points_jugg", "prior_jugg_salary"),
    "espn_value_only": ("espn_salary_cap_value",),
    "espn_value_and_adp": ("espn_salary_cap_value", "adp_espn", "adp_yahoo"),
    "full_without_adp": ("espn_salary_cap_value", "projected_points_jugg", "prior_jugg_salary"),
    "full_without_projection": ("espn_salary_cap_value", "adp_espn", "adp_yahoo", "prior_jugg_salary"),
    "full_without_prior_price": ("espn_salary_cap_value", "adp_espn", "adp_yahoo", "projected_points_jugg"),
    "full": ("espn_salary_cap_value", "adp_espn", "adp_yahoo", "projected_points_jugg", "prior_jugg_salary"),
}
CSV_FIELDS = (
    "season", "internal_player_id", "fantasypros_id", "player_name", "position",
    "nfl_team", "drafted", "jugg_salary", "jugg_owner", "espn_salary_cap_value",
    "espn_overall_rank", "espn_position_rank", "adp_espn", "adp_yahoo",
    "projected_points_jugg", "prior_jugg_salary", "player_pool_source",
)
SCORE_FIELDS = (
    "jugg_price_rank", "internal_player_id", "fantasypros_id", "player_name", "position",
    "nfl_team", "expected_jugg_price_if_drafted", "uncalibrated_model_price", "price_range_low", "price_range_high",
    "range_basis", "draft_probability", "draft_likelihood", "espn_salary_cap_value", "adp_espn", "adp_yahoo",
    "projected_points_jugg", "prior_jugg_salary", "missing_inputs",
)


class ModelError(RuntimeError):
    pass


def training_seasons(target_season: int) -> tuple[int, ...]:
    seasons = tuple(range(2020, target_season))
    if len(seasons) < 2:
        raise ModelError("Target season must be 2022 or later")
    return seasons


def read_pointer(root: Path, pointer: Path) -> tuple[dict[str, Any], Path]:
    reference = json.loads((root / pointer).read_text(encoding="utf-8"))
    artifact = reference.get("artifact")
    if not artifact:
        raise ModelError(f"Pointer has no artifact: {pointer}")
    path = root / artifact
    return json.loads(path.read_text(encoding="utf-8")), path


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_rows(root: Path, seasons: tuple[int, ...] = SEASONS) -> tuple[list[dict[str, Any]], dict[str, str]]:
    sales_payload, sales_path = read_pointer(root, Path("data/processed/auction_history_matches/latest.json"))
    sales = {(row["season"], row["internal_player_id"]): row for row in sales_payload["sales"]}
    if len(sales) != len(sales_payload["sales"]):
        raise ModelError("Auction history has duplicate player-season sales")

    rows: list[dict[str, Any]] = []
    inputs = {str(sales_path.relative_to(root)): checksum(sales_path)}
    prior_salary: dict[str, int] = {}
    # Accepted legacy drafts do not have the contemporaneous market inputs needed
    # to become training rows. They still provide observed league prior prices for
    # players that can be matched unambiguously to a durable current identity.
    for sale in sorted(sales_payload["sales"], key=lambda row: row["season"]):
        if sale["season"] < min(seasons) and sale["internal_player_id"]:
            prior_salary[sale["internal_player_id"]] = sale["salary"]
    for season in seasons:
        canonical, canonical_path = read_pointer(
            root, Path(f"data/processed/canonical_projections/{season}/latest.json")
        )
        espn, espn_path = read_pointer(
            root, Path(f"data/processed/espn_salary_cap_values/{season}/latest.json")
        )
        inputs[str(canonical_path.relative_to(root))] = checksum(canonical_path)
        inputs[str(espn_path.relative_to(root))] = checksum(espn_path)
        canonical_by_id = {p["internal_player_id"]: p for p in canonical["players"]}
        espn_by_id = {p["internal_player_id"]: p for p in espn["values"]}
        season_sales = {pid: sale for (sale_season, pid), sale in sales.items() if sale_season == season}
        pool_ids = set(espn_by_id) | set(season_sales)
        for player_id in sorted(pool_ids):
            sale = season_sales.get(player_id)
            value = espn_by_id.get(player_id)
            player = canonical_by_id.get(player_id)
            if not player and not value and not sale:
                raise ModelError(f"No player metadata for {season} {player_id}")
            market = (player or {}).get("market_signals", {})
            fp = (player or {}).get("fantasypros", {})
            rows.append({
                "season": season,
                "internal_player_id": player_id,
                "fantasypros_id": (player or {}).get("source_ids", {}).get("fantasypros") or (value or {}).get("fantasypros_id") or (sale or {}).get("fantasypros_id"),
                "player_name": (player or {}).get("name") or (value or {}).get("player_name") or sale["player_name"],
                "position": (player or {}).get("position") or (value or {}).get("position") or sale["position"],
                "nfl_team": (player or {}).get("nfl_team") or (value or {}).get("nfl_team") or (sale or {}).get("nfl_team"),
                "drafted": sale is not None,
                "jugg_salary": sale.get("salary") if sale else None,
                "jugg_owner": sale.get("owner") if sale else None,
                "espn_salary_cap_value": value.get("salary_cap_value") if value else None,
                "espn_overall_rank": value.get("overall_rank") if value else None,
                "espn_position_rank": value.get("position_rank") if value else None,
                "adp_espn": market.get("adp_espn"),
                "adp_yahoo": market.get("adp_yahoo"),
                "projected_points_jugg": fp.get("league_projected_points"),
                "prior_jugg_salary": prior_salary.get(player_id),
                "player_pool_source": "espn_and_jugg" if value and sale else "espn" if value else "jugg_exception",
            })
        for player_id, sale in season_sales.items():
            prior_salary[player_id] = sale["salary"]
    return rows, inputs


def build_scoring_rows(root: Path, historical_rows: list[dict[str, Any]], season: int = 2026) -> tuple[list[dict[str, Any]], dict[str, str]]:
    canonical, canonical_path = read_pointer(
        root, Path(f"data/processed/canonical_projections/{season}/latest.json")
    )
    espn, espn_path = read_pointer(
        root, Path(f"data/processed/espn_salary_cap_values/{season}/latest.json")
    )
    espn_by_id = {row["internal_player_id"]: row for row in espn["values"]}
    latest_prior = {}
    for row in sorted((row for row in historical_rows if row["drafted"]), key=lambda row: row["season"]):
        latest_prior[row["internal_player_id"]] = row["jugg_salary"]
    rows = []
    for player in canonical["players"]:
        player_id = player["internal_player_id"]
        value = espn_by_id.get(player_id)
        market = player.get("market_signals", {})
        fp = player.get("fantasypros", {})
        rows.append({
            "season": season, "internal_player_id": player_id,
            "fantasypros_id": player.get("source_ids", {}).get("fantasypros"),
            "player_name": player["name"], "position": player["position"],
            "nfl_team": player.get("nfl_team"), "drafted": None, "jugg_salary": None,
            "jugg_owner": None,
            "espn_salary_cap_value": value.get("salary_cap_value") if value else None,
            "espn_overall_rank": value.get("overall_rank") if value else None,
            "espn_position_rank": value.get("position_rank") if value else None,
            "adp_espn": market.get("adp_espn"), "adp_yahoo": market.get("adp_yahoo"),
            "projected_points_jugg": fp.get("league_projected_points"),
            "prior_jugg_salary": latest_prior.get(player_id),
            "player_pool_source": f"canonical_{season}",
        })
    inputs = {
        str(canonical_path.relative_to(root)): checksum(canonical_path),
        str(espn_path.relative_to(root)): checksum(espn_path),
    }
    return rows, inputs


def metrics(pairs: list[tuple[float, float]]) -> dict[str, Any]:
    if not pairs:
        return {"n": 0, "mae": None, "rmse": None, "bias": None}
    errors = [prediction - actual for prediction, actual in pairs]
    return {
        "n": len(pairs),
        "mae": round(sum(abs(error) for error in errors) / len(errors), 3),
        "rmse": round(math.sqrt(sum(error * error for error in errors) / len(errors)), 3),
        "bias": round(sum(errors) / len(errors), 3),
    }


def fit_line(rows: list[dict[str, Any]]) -> tuple[float, float]:
    pairs = [(float(r["espn_salary_cap_value"]), float(r["jugg_salary"])) for r in rows
             if r["drafted"] and r["espn_salary_cap_value"] is not None]
    if len(pairs) < 2:
        raise ModelError("Not enough ESPN/JUGG pairs to fit calibration")
    x_mean = statistics.fmean(x for x, _ in pairs)
    y_mean = statistics.fmean(y for _, y in pairs)
    denominator = sum((x - x_mean) ** 2 for x, _ in pairs)
    slope = sum((x - x_mean) * (y - y_mean) for x, y in pairs) / denominator
    return y_mean - slope * x_mean, slope


def percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    value = ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)
    return round(value, 3)


def position_adjustments(rows: list[dict[str, Any]], prior_weight: float = 10.0) -> dict[str, float]:
    residuals = defaultdict(list)
    all_residuals = []
    for row in rows:
        residual = float(row["jugg_salary"]) - float(row["espn_salary_cap_value"])
        residuals[row["position"]].append(residual)
        all_residuals.append(residual)
    global_mean = statistics.fmean(all_residuals)
    return {
        position: (sum(residuals[position]) + prior_weight * global_mean) / (len(residuals[position]) + prior_weight)
        for position in residuals
    }


def solve_linear_system(matrix: list[list[float]], values: list[float]) -> list[float]:
    augmented = [row[:] + [value] for row, value in zip(matrix, values)]
    size = len(values)
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ModelError("Singular regression system")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                current - factor * pivot_value
                for current, pivot_value in zip(augmented[row], augmented[column])
            ]
    return [augmented[row][-1] for row in range(size)]


def fit_ridge(
    rows: list[dict[str, Any]], feature_names: tuple[str, ...], penalty: float = 1.0
) -> dict[str, Any]:
    def feature_value(row: dict[str, Any], feature: str) -> float | None:
        value = row.get(feature)
        if value is None:
            return None
        return float(value)

    medians = {}
    for feature in feature_names:
        observed = [value for row in rows if (value := feature_value(row, feature)) is not None]
        medians[feature] = statistics.median(observed) if observed else 0.0

    columns = [f"position={position}" for position in POSITIONS[:-1]]
    for feature in feature_names:
        columns.extend((feature, f"log1p_{feature}", f"sqrt_{feature}", f"{feature}_missing"))

    def raw_vector(row: dict[str, Any]) -> list[float]:
        vector = [1.0 if row["position"] == position else 0.0 for position in POSITIONS[:-1]]
        for feature in feature_names:
            observed = feature_value(row, feature)
            missing = observed is None
            value = medians[feature] if missing else observed
            vector.extend((value, math.log1p(max(0.0, value)), math.sqrt(max(0.0, value)), 1.0 if missing else 0.0))
        return vector

    raw = [raw_vector(row) for row in rows]
    means = [statistics.fmean(vector[index] for vector in raw) for index in range(len(columns))]
    scales = []
    for index, mean in enumerate(means):
        variance = statistics.fmean((vector[index] - mean) ** 2 for vector in raw)
        scales.append(math.sqrt(variance) if variance > 1e-12 else 1.0)
    design = [[1.0] + [(value - mean) / scale for value, mean, scale in zip(vector, means, scales)] for vector in raw]
    targets = [float(row["jugg_salary"]) for row in rows]
    width = len(design[0])
    gram = [[sum(vector[i] * vector[j] for vector in design) for j in range(width)] for i in range(width)]
    for index in range(1, width):
        gram[index][index] += penalty
    rhs = [sum(vector[index] * target for vector, target in zip(design, targets)) for index in range(width)]
    return {
        "feature_names": feature_names, "columns": columns, "medians": medians,
        "means": means, "scales": scales, "coefficients": solve_linear_system(gram, rhs),
    }


def predict_ridge(model: dict[str, Any], row: dict[str, Any], minimum: float | None = 1.0) -> float:
    vector = [1.0 if row["position"] == position else 0.0 for position in POSITIONS[:-1]]
    for feature in model["feature_names"]:
        observed = row.get(feature)
        missing = observed is None
        value = model["medians"][feature] if missing else float(observed)
        vector.extend((value, math.log1p(max(0.0, value)), math.sqrt(max(0.0, value)), 1.0 if missing else 0.0))
    standardized = [
        (value - mean) / scale for value, mean, scale in zip(vector, model["means"], model["scales"])
    ]
    prediction = model["coefficients"][0] + sum(
        coefficient * value for coefficient, value in zip(model["coefficients"][1:], standardized)
    )
    return max(minimum, prediction) if minimum is not None else prediction


def fit_knn(rows: list[dict[str, Any]], feature_names: tuple[str, ...], neighbors: int) -> dict[str, Any]:
    medians = {
        feature: statistics.median([float(row[feature]) for row in rows if row.get(feature) is not None])
        if any(row.get(feature) is not None for row in rows) else 0.0
        for feature in feature_names
    }

    def raw_vector(row: dict[str, Any]) -> list[float]:
        vector = [2.0 if row["position"] == position else 0.0 for position in POSITIONS]
        for feature in feature_names:
            missing = row.get(feature) is None
            value = medians[feature] if missing else float(row[feature])
            vector.extend((value, math.log1p(max(0.0, value)), math.sqrt(max(0.0, value)), 1.0 if missing else 0.0))
        return vector

    raw = [raw_vector(row) for row in rows]
    means = [statistics.fmean(vector[index] for vector in raw) for index in range(len(raw[0]))]
    scales = []
    for index, mean in enumerate(means):
        variance = statistics.fmean((vector[index] - mean) ** 2 for vector in raw)
        scales.append(math.sqrt(variance) if variance > 1e-12 else 1.0)
    vectors = [[(value - mean) / scale for value, mean, scale in zip(vector, means, scales)] for vector in raw]
    return {
        "feature_names": feature_names, "neighbors": min(neighbors, len(rows)), "medians": medians,
        "means": means, "scales": scales, "vectors": vectors,
        "targets": [float(row["jugg_salary"]) for row in rows],
    }


def predict_knn(model: dict[str, Any], row: dict[str, Any], minimum: float | None = 1.0) -> float:
    raw = [2.0 if row["position"] == position else 0.0 for position in POSITIONS]
    for feature in model["feature_names"]:
        missing = row.get(feature) is None
        value = model["medians"][feature] if missing else float(row[feature])
        raw.extend((value, math.log1p(max(0.0, value)), math.sqrt(max(0.0, value)), 1.0 if missing else 0.0))
    vector = [(value - mean) / scale for value, mean, scale in zip(raw, model["means"], model["scales"])]
    distances = sorted(
        (sum((left - right) ** 2 for left, right in zip(vector, candidate)), target)
        for candidate, target in zip(model["vectors"], model["targets"])
    )[:model["neighbors"]]
    exact = [target for distance, target in distances if distance < 1e-12]
    if exact:
        prediction = statistics.fmean(exact)
        return max(minimum, prediction) if minimum is not None else prediction
    weights = [(1.0 / math.sqrt(distance), target) for distance, target in distances]
    prediction = sum(weight * target for weight, target in weights) / sum(weight for weight, _ in weights)
    return max(minimum, prediction) if minimum is not None else prediction


def probability_metrics(predictions: list[tuple[float, int]]) -> dict[str, Any]:
    if not predictions:
        return {"n": 0, "brier": None, "log_loss": None, "auc": None}
    clipped = [(min(1 - 1e-9, max(1e-9, probability)), actual) for probability, actual in predictions]
    positives = [probability for probability, actual in clipped if actual == 1]
    negatives = [probability for probability, actual in clipped if actual == 0]
    comparisons = sum(
        1.0 if positive > negative else 0.5 if positive == negative else 0.0
        for positive in positives for negative in negatives
    )
    return {
        "n": len(clipped), "positive_count": len(positives),
        "brier": round(statistics.fmean((probability - actual) ** 2 for probability, actual in clipped), 4),
        "log_loss": round(-statistics.fmean(actual * math.log(probability) + (1 - actual) * math.log(1 - probability) for probability, actual in clipped), 4),
        "auc": round(comparisons / (len(positives) * len(negatives)), 4) if positives and negatives else None,
    }


def probability_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**row, "jugg_salary": 1.0 if row["drafted"] else 0.0} for row in rows]


def predict_probability(model: dict[str, Any], row: dict[str, Any], family: str) -> float:
    prediction = predict_ridge(model, row, None) if family == "ridge" else predict_knn(model, row, None)
    return min(1.0, max(0.0, prediction))


def choose_probability_parameter(
    rows: list[dict[str, Any]], feature_names: tuple[str, ...], family: str
) -> float | int:
    seasons = sorted({row["season"] for row in rows})
    candidates: list[float | int] = [0.1, 1.0, 10.0, 100.0] if family == "ridge" else [5, 15, 30, 60]
    if len(seasons) < 2:
        return 1.0 if family == "ridge" else 15
    validation_season = seasons[-1]
    training = probability_rows([row for row in rows if row["season"] < validation_season])
    validation = [row for row in rows if row["season"] == validation_season]
    scores = []
    for candidate in candidates:
        model = fit_ridge(training, feature_names, float(candidate)) if family == "ridge" else fit_knn(training, feature_names, int(candidate))
        pairs = [(predict_probability(model, row, family), 1 if row["drafted"] else 0) for row in validation]
        scores.append((probability_metrics(pairs)["brier"], candidate))
    return min(scores)[1]


def draft_probability_tournament(rows: list[dict[str, Any]], seasons: tuple[int, ...] = SEASONS) -> dict[str, Any]:
    pool = [row for row in rows if row.get("espn_salary_cap_value") is not None or row.get("adp_yahoo") is not None]
    feature_sets = {
        "adp_only": MODEL_FEATURES["adp_only"],
        "espn_value_only": MODEL_FEATURES["espn_value_only"],
        "projection_only": MODEL_FEATURES["projection_only"],
        "market_without_espn_value": MODEL_FEATURES["market_without_espn_value"],
        "full": MODEL_FEATURES["full"],
    }
    accumulated: dict[str, list[tuple[float, int, dict[str, Any]]]] = {}
    by_season = {}
    for season in seasons[1:]:
        training = [row for row in pool if row["season"] < season]
        test = [row for row in pool if row["season"] == season]
        by_season[str(season)] = {}
        for feature_set, features in feature_sets.items():
            for family in ("ridge", "knn"):
                name = f"{family}:{feature_set}"
                parameter = choose_probability_parameter(training, features, family)
                binary_training = probability_rows(training)
                model = fit_ridge(binary_training, features, float(parameter)) if family == "ridge" else fit_knn(binary_training, features, int(parameter))
                predictions = [(predict_probability(model, row, family), 1 if row["drafted"] else 0, row) for row in test]
                accumulated.setdefault(name, []).extend(predictions)
                by_season[str(season)][name] = probability_metrics([(p, a) for p, a, _ in predictions])
    overall = {name: probability_metrics([(p, a) for p, a, _ in values]) for name, values in accumulated.items()}
    ranking = sorted(({"model": name, **score} for name, score in overall.items()), key=lambda row: (row["brier"], -row["auc"], row["model"]))
    best = ranking[0]["model"]
    best_predictions = accumulated[best]
    top_pool = sorted(best_predictions, key=lambda item: item[0], reverse=True)
    by_year_top_140 = {}
    for season in seasons[1:]:
        season_predictions = sorted((item for item in best_predictions if item[2]["season"] == season), key=lambda item: item[0], reverse=True)[:140]
        hits = sum(actual for _, actual, _ in season_predictions)
        eligible_actuals = sum(row["drafted"] for row in pool if row["season"] == season)
        by_year_top_140[str(season)] = {
            "hits": hits, "precision": round(hits / len(season_predictions), 4),
            "recall_of_eligible_draftees": round(hits / eligible_actuals, 4),
        }
    calibration = []
    for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
        bucket = [(p, a) for p, a, _ in best_predictions if lower <= p < lower + 0.2 or (lower == 0.8 and p == 1.0)]
        if bucket:
            calibration.append({
                "range": f"{lower:.1f}-{lower + 0.2:.1f}", "n": len(bucket),
                "mean_prediction": round(statistics.fmean(p for p, _ in bucket), 4),
                "actual_draft_rate": round(statistics.fmean(a for _, a in bucket), 4),
            })
    return {
        "cohort": "historical players with an ESPN Salary Cap Value or Yahoo ADP",
        "training_rule": "forward-only, with time-aware inner tuning",
        "ranking": ranking, "best_model": best, "by_test_season": by_season,
        "best_model_top_140_by_season": by_year_top_140,
        "best_model_calibration": calibration,
        "row_count": len(best_predictions),
    }


def choose_parameter(
    rows: list[dict[str, Any]], feature_names: tuple[str, ...], family: str
) -> float | int:
    seasons = sorted({row["season"] for row in rows})
    candidates: list[float | int] = [0.1, 1.0, 10.0, 100.0] if family == "ridge" else [5, 15, 30, 60]
    if len(seasons) < 2:
        return 1.0 if family == "ridge" else 15
    validation_season = seasons[-1]
    inner_train = [row for row in rows if row["season"] < validation_season]
    validation = [row for row in rows if row["season"] == validation_season]
    scores = []
    for candidate in candidates:
        if family == "ridge":
            model = fit_ridge(inner_train, feature_names, float(candidate))
            pairs = [(predict_ridge(model, row), float(row["jugg_salary"])) for row in validation]
        else:
            model = fit_knn(inner_train, feature_names, int(candidate))
            pairs = [(predict_knn(model, row), float(row["jugg_salary"])) for row in validation]
        scores.append((metrics(pairs)["mae"], candidate))
    return min(scores)[1]


def calibrate_draft_probabilities(probabilities: list[float], draft_slots: int) -> list[float]:
    """Adjust probability odds so expected drafted players equal the league slots."""
    probability_floor, probability_ceiling = 0.005, 0.995

    def calibrated(probability: float, multiplier: float) -> float:
        adjusted = (multiplier * probability) / (1 - probability + multiplier * probability)
        return min(probability_ceiling, max(probability_floor, adjusted))

    low, high = 0.0, 1000.0
    for _ in range(80):
        multiplier = (low + high) / 2
        if sum(calibrated(probability, multiplier) for probability in probabilities) < draft_slots:
            low = multiplier
        else:
            high = multiplier
    multiplier = (low + high) / 2
    return [calibrated(probability, multiplier) for probability in probabilities]


def economy_calibrate_prices(
    prices: list[float], probabilities: list[float], method: str,
    draft_slots: int = 140, total_budget: int = 2000,
) -> tuple[list[float], dict[str, Any]]:
    """Reconcile conditional prices to the league economy without using outcomes."""
    if len(prices) != len(probabilities):
        raise ModelError("Price and probability counts differ")
    if len(prices) < draft_slots:
        raise ModelError("Not enough supported players for league economy calibration")
    ranked_indexes = sorted(range(len(prices)), key=lambda index: (-prices[index], index))
    top_indexes = ranked_indexes[:draft_slots]
    minimum_total = sum(probabilities)

    if method == "raw_unconstrained":
        calibrated = list(prices)
        adjustment = 1.0
    elif method == "top_140_proportional":
        denominator = sum(max(0.0, prices[index] - 1.0) for index in top_indexes)
        adjustment = (total_budget - draft_slots) / denominator
        calibrated = [1.0 + adjustment * max(0.0, price - 1.0) for price in prices]
    elif method == "top_140_additive":
        low, high = -100.0, 100.0
        for _ in range(80):
            delta = (low + high) / 2
            if sum(max(1.0, prices[index] + delta) for index in top_indexes) < total_budget:
                low = delta
            else:
                high = delta
        adjustment = (low + high) / 2
        calibrated = [max(1.0, price + adjustment) for price in prices]
    elif method == "top_140_premium_preserving":
        protected = {index for index in top_indexes if prices[index] >= 30.0}
        protected_total = sum(prices[index] for index in protected)
        adjustable = [index for index in top_indexes if index not in protected]
        low, high = -100.0, 100.0
        for _ in range(80):
            delta = (low + high) / 2
            if protected_total + sum(max(1.0, prices[index] + delta) for index in adjustable) < total_budget:
                low = delta
            else:
                high = delta
        adjustment = (low + high) / 2
        calibrated = [price if price >= 30.0 else max(1.0, price + adjustment) for price in prices]
    elif method == "probability_weighted_additive":
        low, high = -100.0, 100.0
        for _ in range(80):
            delta = (low + high) / 2
            expected = sum(
                probability * max(1.0, price + delta)
                for price, probability in zip(prices, probabilities)
            )
            if expected < total_budget:
                low = delta
            else:
                high = delta
        adjustment = (low + high) / 2
        calibrated = [max(1.0, price + adjustment) for price in prices]
    elif method == "probability_weighted_proportional":
        denominator = sum(
            probability * max(0.0, price - 1.0)
            for price, probability in zip(prices, probabilities)
        )
        adjustment = (total_budget - minimum_total) / denominator
        calibrated = [1.0 + adjustment * max(0.0, price - 1.0) for price in prices]
    else:
        raise ModelError(f"Unknown economy calibration method: {method}")

    return calibrated, {
        "method": method,
        "adjustment": round(adjustment, 6),
        "top_140_total": round(sum(calibrated[index] for index in top_indexes), 3),
        "probability_weighted_total": round(sum(
            probability * price for price, probability in zip(calibrated, probabilities)
        ), 3),
    }


def economy_calibration_tournament(rows: list[dict[str, Any]], seasons: tuple[int, ...] = SEASONS) -> dict[str, Any]:
    """Forward-test competing ways to reconcile conditional prices to $2,000."""
    sold = [row for row in rows if row["drafted"]]
    pool = [
        row for row in rows
        if row.get("espn_salary_cap_value") is not None or row.get("adp_yahoo") is not None
    ]
    if any(sum(row["season"] == season for row in pool) < 140 for season in seasons[1:]):
        return {
            "status": "insufficient_pool",
            "required_supported_players_per_test_season": 140,
        }
    methods = (
        "raw_unconstrained", "top_140_proportional", "top_140_additive",
        "top_140_premium_preserving", "probability_weighted_additive",
        "probability_weighted_proportional",
    )
    predictions: dict[str, list[tuple[float, float]]] = {method: [] for method in methods}
    by_season: dict[str, dict[str, Any]] = {}
    for season in seasons[1:]:
        price_training = [row for row in sold if row["season"] < season]
        probability_training = [row for row in pool if row["season"] < season]
        test = [row for row in pool if row["season"] == season]
        price_penalty = choose_parameter(price_training, MODEL_FEATURES["full"], "ridge")
        price_model = fit_ridge(price_training, MODEL_FEATURES["full"], float(price_penalty))
        prices = [predict_ridge(price_model, row) for row in test]
        probability_penalty = choose_probability_parameter(
            probability_training, MODEL_FEATURES["full"], "ridge"
        )
        probability_model = fit_ridge(
            probability_rows(probability_training), MODEL_FEATURES["full"],
            float(probability_penalty),
        )
        raw_probabilities = [
            min(1 - 1e-6, max(1e-6, predict_probability(probability_model, row, "ridge")))
            for row in test
        ]
        probabilities = calibrate_draft_probabilities(raw_probabilities, 140)
        by_season[str(season)] = {}
        for method in methods:
            calibrated, economy = economy_calibrate_prices(prices, probabilities, method)
            pairs = [
                (prediction, float(row["jugg_salary"]))
                for prediction, row in zip(calibrated, test) if row["drafted"]
            ]
            predictions[method].extend(pairs)
            by_season[str(season)][method] = {**metrics(pairs), **economy}

    ranking = []
    for method, pairs in predictions.items():
        ranking.append({
            "method": method, **metrics(pairs),
            "price_50_plus": metrics([(p, a) for p, a in pairs if a >= 50]),
            "price_60_plus": metrics([(p, a) for p, a in pairs if a >= 60]),
        })
    ranking.sort(key=lambda row: (row["price_50_plus"]["mae"], row["mae"], row["method"]))
    return {
        "training_rule": "forward-only price and draft-probability models; no evaluated season informs its calibration",
        "selection_rule": "among economy-coherent methods, prioritize $50+ MAE while requiring overall MAE to remain within 1% of the raw model",
        "production_method": "probability_weighted_proportional",
        "ranking_by_premium_mae": ranking,
        "by_test_season": by_season,
        "interpretation": "Conditional prices are reconciled so probability-weighted expected spending equals $2,000; the identities of the 140 drafted players are not assumed known.",
    }


def neutral_model_tournament(rows: list[dict[str, Any]], seasons: tuple[int, ...] = SEASONS) -> dict[str, Any]:
    sold = [row for row in rows if row["drafted"]]
    test_seasons = seasons[1:]
    results: dict[str, list[tuple[float, float, dict[str, Any]]]] = {}
    by_season: dict[str, dict[str, Any]] = {}
    selected_parameters: dict[str, dict[str, Any]] = {}
    for season in test_seasons:
        training = [row for row in sold if row["season"] < season]
        test = [row for row in sold if row["season"] == season]
        by_season[str(season)] = {}
        selected_parameters[str(season)] = {}
        for feature_set, feature_names in MODEL_FEATURES.items():
            for family in ("ridge", "knn"):
                name = f"{family}:{feature_set}"
                parameter = choose_parameter(training, feature_names, family)
                if family == "ridge":
                    model = fit_ridge(training, feature_names, float(parameter))
                    predictions = [(predict_ridge(model, row), float(row["jugg_salary"]), row) for row in test]
                else:
                    model = fit_knn(training, feature_names, int(parameter))
                    predictions = [(predict_knn(model, row), float(row["jugg_salary"]), row) for row in test]
                results.setdefault(name, []).extend(predictions)
                by_season[str(season)][name] = metrics([(prediction, actual) for prediction, actual, _ in predictions])
                selected_parameters[str(season)][name] = parameter
    overall = {
        name: metrics([(prediction, actual) for prediction, actual, _ in predictions])
        for name, predictions in results.items()
    }
    ranked = sorted(
        ({"model": name, **score} for name, score in overall.items()),
        key=lambda row: (row["mae"], row["rmse"], row["model"]),
    )
    best_name = ranked[0]["model"]
    best_predictions = results[best_name]
    by_position = {
        position: metrics([(prediction, actual) for prediction, actual, row in best_predictions if row["position"] == position])
        for position in POSITIONS
    }
    by_tier = {}
    for label, lower, upper in (("1", 1, 1), ("2_to_5", 2, 5), ("6_to_15", 6, 15), ("16_to_30", 16, 30), ("31_plus", 31, math.inf)):
        by_tier[label] = metrics([
            (prediction, actual) for prediction, actual, _ in best_predictions if lower <= actual <= upper
        ])
    absolute_errors = [abs(prediction - actual) for prediction, actual, _ in best_predictions]
    error_ranges = {
        "overall": {"p50": percentile(absolute_errors, 0.50), "p80": percentile(absolute_errors, 0.80), "p90": percentile(absolute_errors, 0.90)},
        "by_position": {},
    }
    for position in POSITIONS:
        errors = [abs(prediction - actual) for prediction, actual, row in best_predictions if row["position"] == position]
        error_ranges["by_position"][position] = {
            "n": len(errors), "p50": percentile(errors, 0.50),
            "p80": percentile(errors, 0.80), "p90": percentile(errors, 0.90),
        }
    coverage = {
        feature: {
            "observed": sum(row.get(feature) is not None for row in sold),
            "total": len(sold),
            "percent": round(100 * sum(row.get(feature) is not None for row in sold) / len(sold), 2),
        }
        for feature in ("espn_salary_cap_value", "adp_espn", "adp_yahoo", "projected_points_jugg", "prior_jugg_salary")
    }
    return {
        "cohort": f"all JUGG sales from {test_seasons[0]}-{test_seasons[-1]}; cohort membership is independent of every candidate feature",
        "training_rule": "for test season Y, train only on seasons earlier than Y",
        "tuning_rule": "choose ridge penalty or neighbor count using the latest training season as an inner forward validation set when available",
        "feature_rule": "every numeric input receives raw, log1p, and square-root bases plus a missing indicator; all models include position",
        "model_families": ["ridge_regression", "distance_weighted_knn"],
        "row_count": sum(1 for row in sold if row["season"] in test_seasons),
        "coverage_all_sold_seasons": coverage,
        "ranking": ranked,
        "by_test_season": by_season,
        "selected_parameters": selected_parameters,
        "best_model": best_name,
        "best_model_by_position": by_position,
        "best_model_by_actual_price_tier": by_tier,
        "best_model_absolute_error": error_ranges,
    }


def score_season(
    historical_rows: list[dict[str, Any]], scoring_rows: list[dict[str, Any]], tournament: dict[str, Any],
    probability_tournament: dict[str, Any], season: int = 2026,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    training = [row for row in historical_rows if row["drafted"]]
    feature_names = MODEL_FEATURES["full"]
    penalty = choose_parameter(training, feature_names, "ridge")
    model = fit_ridge(training, feature_names, float(penalty))
    error_ranges = tournament["best_model_absolute_error"]
    eligible = [
        row for row in scoring_rows
        if row.get("espn_salary_cap_value") is not None or row.get("adp_yahoo") is not None
    ]
    scored = []
    for row in eligible:
        prediction = predict_ridge(model, row)
        missing = [feature for feature in feature_names if row.get(feature) is None]
        scored.append({
            **row,
            "uncalibrated_model_price": prediction,
            "missing_inputs": missing,
        })
    draft_slots = 140
    total_budget = 2000
    probability_pool = [
        row for row in historical_rows
        if row.get("espn_salary_cap_value") is not None or row.get("adp_yahoo") is not None
    ]
    family, feature_set = probability_tournament["best_model"].split(":", 1)
    probability_features = MODEL_FEATURES[feature_set]
    probability_parameter = choose_probability_parameter(probability_pool, probability_features, family)
    binary_training = probability_rows(probability_pool)
    probability_model = fit_ridge(binary_training, probability_features, float(probability_parameter)) if family == "ridge" else fit_knn(binary_training, probability_features, int(probability_parameter))
    raw_probabilities = [min(1 - 1e-6, max(1e-6, predict_probability(probability_model, row, family))) for row in scored]
    calibrated_probabilities = calibrate_draft_probabilities(raw_probabilities, draft_slots)
    for row, calibrated in zip(scored, calibrated_probabilities):
        row["draft_probability"] = round(calibrated, 4)
        row["draft_likelihood"] = (
            "very_likely" if calibrated >= 0.8 else "likely" if calibrated >= 0.6
            else "bubble" if calibrated >= 0.4 else "long_shot" if calibrated >= 0.2 else "unlikely"
        )
    calibrated_prices, economy = economy_calibrate_prices(
        [row["uncalibrated_model_price"] for row in scored], calibrated_probabilities,
        "probability_weighted_proportional", draft_slots, total_budget,
    )
    for row, calibrated in zip(scored, calibrated_prices):
        position_range = error_ranges["by_position"].get(row["position"], {})
        radius = (position_range.get("p80") or error_ranges["overall"]["p80"]) * economy["adjustment"]
        row.update({
            "expected_jugg_price_if_drafted": round(calibrated, 1),
            "uncalibrated_model_price": round(row["uncalibrated_model_price"], 1),
            "price_range_low": round(max(1.0, calibrated - radius), 1),
            "price_range_high": round(calibrated + radius, 1),
            "range_basis": f"historical_forward_error_p80:{row['position']}",
        })
    scored.sort(key=lambda row: (-row["expected_jugg_price_if_drafted"], row["player_name"]))
    for rank, row in enumerate(scored, start=1):
        row["jugg_price_rank"] = rank
    metadata = {
        "season": season, "model": "ridge:full", "training_seasons": sorted({row["season"] for row in historical_rows}),
        "training_sale_count": len(training), "selected_ridge_penalty": penalty,
        "score_count": len(scored), "excluded_out_of_scope_count": len(scoring_rows) - len(scored),
        "scoring_eligibility": f"Player has a {season} ESPN Salary Cap Value or Yahoo ADP; deeper canonical players are excluded as outside the historical model's supported sale-price population.",
        "league_economy_calibration": {
            "draft_slots": draft_slots, "total_budget": total_budget,
            "minimum_price": 1, **economy,
            "interpretation": "Draft probabilities weight conditional prices so expected league spending equals the fixed budget without assuming which 140 players are drafted.",
        },
        "complete_input_count": sum(not row["missing_inputs"] for row in scored),
        "missing_input_counts": {
            feature: sum(feature in row["missing_inputs"] for row in scored) for feature in feature_names
        },
        "interpretation": "Price is conditional on being drafted; draft_probability is a separate model output. Neither is a production value.",
        "draft_probability_model": {
            "model": probability_tournament["best_model"], "selected_parameter": probability_parameter,
            "training_pool_count": len(probability_pool),
            "probability_floor": 0.005, "probability_ceiling": 0.995,
            "expected_drafted_count": round(sum(row["draft_probability"] for row in scored), 4),
            "interpretation": f"Probability that the player occupies one of the 140 JUGG draft slots, calibrated to sum to 140 across the supported {season} pool.",
        },
    }
    return scored, metadata


def ablation_study(rows: list[dict[str, Any]], seasons: tuple[int, ...] = SEASONS) -> dict[str, Any]:
    common = [row for row in rows if row["drafted"] and row["espn_salary_cap_value"] is not None]
    predictions: dict[str, list[tuple[float, float]]] = {name: [] for name in MODEL_FEATURES}
    season_results: dict[str, dict[str, Any]] = {}
    for season in seasons:
        training = [row for row in common if row["season"] != season]
        test = [row for row in common if row["season"] == season]
        season_results[str(season)] = {}
        for name, features in MODEL_FEATURES.items():
            model = fit_ridge(training, features)
            pairs = [(predict_ridge(model, row), float(row["jugg_salary"])) for row in test]
            predictions[name].extend(pairs)
            season_results[str(season)][name] = metrics(pairs)
    overall = {name: metrics(pairs) for name, pairs in predictions.items()}
    full_mae = overall["full"]["mae"]
    without_espn_mae = overall["market_without_espn_value"]["mae"]
    without_adp_mae = overall["full_without_adp"]["mae"]
    return {
        "cohort": "drafted player-seasons with an ESPN Salary Cap Value",
        "row_count": len(common),
        "method": "ridge regression with position controls, log-transformed ADP, training-set median imputation, missing indicators, and leave-one-season-out evaluation",
        "overall": overall,
        "by_held_out_season": season_results,
        "espn_incremental_mae_improvement": round(without_espn_mae - full_mae, 3),
        "espn_incremental_mae_improvement_percent": round(100 * (without_espn_mae - full_mae) / without_espn_mae, 2),
        "adp_incremental_mae_improvement": round(without_adp_mae - full_mae, 3),
        "adp_incremental_mae_improvement_percent": round(100 * (without_adp_mae - full_mae) / without_adp_mae, 2),
    }


def evaluate(rows: list[dict[str, Any]], seasons: tuple[int, ...] = SEASONS) -> dict[str, Any]:
    sold_with_espn = [r for r in rows if r["drafted"] and r["espn_salary_cap_value"] is not None]
    raw_pairs = [(float(r["espn_salary_cap_value"]), float(r["jugg_salary"])) for r in sold_with_espn]
    by_season = {}
    held_out_predictions = []
    position_predictions = []
    coefficients = {}
    for season in seasons:
        training = [r for r in sold_with_espn if r["season"] != season]
        test = [r for r in sold_with_espn if r["season"] == season]
        intercept, slope = fit_line(training)
        adjustments = position_adjustments(training)
        pairs = [(max(1.0, intercept + slope * float(r["espn_salary_cap_value"])), float(r["jugg_salary"])) for r in test]
        position_pairs = [
            (max(1.0, float(r["espn_salary_cap_value"]) + adjustments.get(r["position"], 0.0)), float(r["jugg_salary"]))
            for r in test
        ]
        held_out_predictions.extend(pairs)
        position_predictions.extend(position_pairs)
        coefficients[str(season)] = {"intercept": round(intercept, 6), "espn_slope": round(slope, 6)}
        by_season[str(season)] = {
            "espn_raw": metrics([(float(r["espn_salary_cap_value"]), float(r["jugg_salary"])) for r in test]),
            "espn_calibrated_held_out": metrics(pairs),
            "espn_position_adjusted_held_out": metrics(position_pairs),
            "drafted_players": sum(r["drafted"] for r in rows if r["season"] == season),
            "drafted_with_espn": len(test),
            "espn_pool_size": sum(r["espn_salary_cap_value"] is not None for r in rows if r["season"] == season),
        }
    by_position = {}
    for position in POSITIONS:
        position_rows = [r for r in sold_with_espn if r["position"] == position]
        by_position[position] = metrics([
            (float(r["espn_salary_cap_value"]), float(r["jugg_salary"])) for r in position_rows
        ])
    pool_sources = Counter(r["player_pool_source"] for r in rows)
    raw_absolute_errors = [abs(prediction - actual) for prediction, actual in raw_pairs]
    return {
        "dataset": {
            "row_count": len(rows), "drafted_count": sum(r["drafted"] for r in rows),
            "drafted_with_espn_count": len(sold_with_espn), "pool_sources": dict(pool_sources),
        },
        "baselines": {
            "espn_raw_overall": metrics(raw_pairs),
            "espn_calibrated_leave_one_season_out": metrics(held_out_predictions),
            "espn_position_adjusted_leave_one_season_out": metrics(position_predictions),
            "by_season": by_season, "espn_raw_by_position": by_position,
        },
        "uncertainty": {
            "espn_raw_absolute_error": {
                "p50": percentile(raw_absolute_errors, 0.50),
                "p80": percentile(raw_absolute_errors, 0.80),
                "p90": percentile(raw_absolute_errors, 0.90),
            }
        },
        "calibration_coefficients_by_held_out_season": coefficients,
        "ablation_study": ablation_study(rows, seasons),
        "neutral_model_tournament": neutral_model_tournament(rows, seasons),
        "economy_calibration_tournament": economy_calibration_tournament(rows, seasons),
        "draft_probability_tournament": draft_probability_tournament(rows, seasons),
        "notes": [
            "Sale-price errors are evaluated only for drafted players with an ESPN value.",
            "The calibrated baseline is fit without the evaluated season; it is not a random row split.",
            "Drafted probability and prediction intervals are reserved for the next model iteration.",
        ],
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field) for field in CSV_FIELDS} for row in rows)


def write_scores_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCORE_FIELDS)
        writer.writeheader()
        for row in rows:
            output = {field: row.get(field) for field in SCORE_FIELDS}
            output["missing_inputs"] = ";".join(row["missing_inputs"])
            writer.writerow(output)


def run(root: Path, season: int = 2026) -> Path:
    seasons = training_seasons(season)
    rows, inputs = build_rows(root, seasons)
    report = evaluate(rows, seasons)
    scoring_rows, scoring_inputs = build_scoring_rows(root, rows, season)
    scores, scoring_metadata = score_season(
        rows, scoring_rows, report["neutral_model_tournament"], report["draft_probability_tournament"], season
    )
    inputs.update(scoring_inputs)
    built_at = datetime.now(timezone.utc)
    build_id = built_at.strftime("%Y%m%dT%H%M%SZ")
    output_dir = root / "data" / "processed" / "auction_price_model" / build_id
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "training_rows.csv", rows)
    scores_csv = output_dir / f"scores_{season}.csv"
    scores_json = output_dir / f"scores_{season}.json"
    write_scores_csv(scores_csv, scores)
    scores_json.write_text(json.dumps({
        "metadata": scoring_metadata, "players": scores,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    payload = {
        "metadata": {"schema_version": 1, "build_id": build_id, "built_at": built_at.isoformat(), "seasons": list(seasons), "target_season": season, "inputs": inputs},
        **report,
    }
    report_path = output_dir / "benchmark.json"
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    pointer = root / "data" / "processed" / "auction_price_model" / "latest.json"
    pointer.write_text(json.dumps({
        "schema_version": 1, "build_id": build_id,
        "benchmark": str(report_path.relative_to(root)),
        "training_rows": str((output_dir / "training_rows.csv").relative_to(root)),
        "target_season": season,
        f"scores_{season}_csv": str(scores_csv.relative_to(root)),
        f"scores_{season}_json": str(scores_json.relative_to(root)),
    }, indent=2) + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--season", type=int, default=2026, help="Season to score; prior seasons become training data")
    args = parser.parse_args()
    try:
        print(f"Wrote {run(args.root.resolve(), args.season)}")
    except (OSError, KeyError, ValueError, json.JSONDecodeError, ModelError) as exc:
        print(f"Auction model benchmark failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
