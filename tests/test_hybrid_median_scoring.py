from scripts.hybrid_median_scoring import calculate_season


def test_hybrid_points_and_rank_change():
    payload = {
        "season": 2025,
        "matchups": [
            {"week": 1, "team1_id": "a", "team1": "A", "score1": 100, "team2_id": "b", "team2": "B", "score2": 90},
            {"week": 1, "team1_id": "c", "team1": "C", "score1": 110, "team2_id": "d", "team2": "D", "score2": 80},
            {"week": 2, "team1_id": "a", "team1": "A", "score1": 70, "team2_id": "c", "team2": "C", "score2": 60},
            {"week": 2, "team1_id": "b", "team1": "B", "score1": 120, "team2_id": "d", "team2": "D", "score2": 110},
        ],
    }

    result = calculate_season(payload)
    rows = {row["team_id"]: row for row in result["standings"]}

    assert rows["a"]["h2h_points"] == 2
    assert rows["a"]["median_points"] == 1
    assert rows["b"]["h2h_points"] == 1
    assert rows["b"]["median_points"] == 1
    assert rows["c"]["median_points"] == 1
    assert result["standings"][0]["team_id"] == "a"


def test_exact_median_does_not_earn_point_and_h2h_ties_split():
    payload = {
        "season": 2025,
        "matchups": [
            {"week": 1, "team1_id": "a", "team1": "A", "score1": 100, "team2_id": "b", "team2": "B", "score2": 100},
            {"week": 1, "team1_id": "c", "team1": "C", "score1": 120, "team2_id": "d", "team2": "D", "score2": 80},
        ],
    }

    rows = {row["team_id"]: row for row in calculate_season(payload)["standings"]}

    assert rows["a"]["h2h_points"] == 0.5
    assert rows["a"]["median_points"] == 0
    assert rows["c"]["median_points"] == 1
