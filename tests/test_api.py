from __future__ import annotations

import importlib
import json

from fastapi.testclient import TestClient

from reef_game.api import app

client = TestClient(app)


def test_health_and_frontend() -> None:
    assert client.get("/api/health").json()["status"] == "ok"
    page = client.get("/")
    assert page.status_code == 200
    assert "Great Coral Reef" in page.text
    assert client.get("/static/styles.css").status_code == 200


def test_game_and_card_catalog() -> None:
    game = client.get("/api/game").json()
    assert game["total_cards"] > 0
    assert game["player_count"] == 4
    assert game["board"] == {"width": 16, "height": 16, "max_layers": 3}
    assert set(game["card_counts"]) == {
        "coral",
        "fauna",
        "soil",
        "instinct",
        "upgrade",
        "climate",
    }

    types = client.get("/api/cards/types").json()
    assert sum(item["count"] for item in types) == game["total_cards"]

    response = client.get("/api/cards", params={"type": "coral", "search": "staghorn"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert all(card["type"] == "coral" for card in body["items"])

    card = body["items"][0]
    detail = client.get(f"/api/cards/coral/{card['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == card["id"]
    assert client.get("/api/cards/coral/not-a-card").status_code == 404


def test_rules() -> None:
    payload = client.get("/api/rules").json()
    assert len(payload["sections"]) >= 5
    assert payload["actions"]
    assert client.get("/api/rules/climate").json()["title"] == "Clima e ambiente"


def test_tournament_catalog_and_files(tmp_path, monkeypatch) -> None:
    api_module = importlib.import_module("reef_game.api.app")
    tournament = tmp_path / "paired_example"
    tournament.mkdir()
    (tournament / "metadata.json").write_text(
        json.dumps(
            {
                "saved_at_utc": "20261101T120000Z",
                "mode": "paired",
                "version": {"code_version": "0.1.0"},
                "tournament_config": {
                    "games": 2,
                    "agent_p1": "greedy",
                    "agent_p2": "longterm",
                },
                "summary": {"paired_games": 4, "a_winrate": 0.5},
            }
        ),
        encoding="utf-8",
    )
    (tournament / "results.csv").write_text(
        "winner,score\ngreedy,10\n", encoding="utf-8"
    )
    (tournament / "report.html").write_text("<h1>Report</h1>", encoding="utf-8")
    monkeypatch.setattr(api_module, "TOURNAMENT_DIR", tmp_path)

    listing = client.get("/api/tournaments").json()
    assert listing["total"] == 1
    assert listing["items"][0]["agents"] == ["greedy", "longterm"]
    assert listing["items"][0]["version"] == "0.1.0"

    detail = client.get("/api/tournaments/paired_example", params={"sample_rows": 1}).json()
    assert detail["samples"]["results.csv"][0]["winner"] == "greedy"
    assert client.get("/api/tournaments/paired_example/report").status_code == 200
    assert client.get("/api/tournaments/paired_example/files/results.csv").status_code == 200
