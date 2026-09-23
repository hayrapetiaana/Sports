from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"


def test_leaguepro_endpoints():
    res_t = client.get("/api/leaguepro/tournaments?date_from=2026-09-18&date_to=2026-09-19")
    assert res_t.status_code == 200
    tournaments = res_t.json()
    assert isinstance(tournaments, list)
    assert len(tournaments) > 0

    res_m = client.get("/api/leaguepro/matches?date_from=2026-09-18&date_to=2026-09-19")
    assert res_m.status_code == 200
    matches_data = res_m.json()
    assert matches_data["total"] > 0
    assert len(matches_data["matches"]) > 0


def test_sportliga_endpoints():
    res_t = client.get("/api/sportliga/tournaments?date_from=2026-09-18&date_to=2026-09-19")
    assert res_t.status_code == 200
    tournaments = res_t.json()
    assert isinstance(tournaments, list)
    assert len(tournaments) > 0

    res_m = client.get("/api/sportliga/matches?date_from=2026-09-18&date_to=2026-09-19")
    assert res_m.status_code == 200
    matches_data = res_m.json()
    assert matches_data["total"] > 0
    assert len(matches_data["matches"]) > 0


def test_unified_matches_all_platforms():
    res = client.get("/api/all/matches?date_from=2026-09-18&date_to=2026-09-19")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
    assert "platform_counts" in data
    assert "counts" in data
    assert len(data["matches"]) == data["total"]

    # Check a sample unified match structure
    sample = data["matches"][0]
    assert "id" in sample
    assert "platform" in sample
    assert "platform_name" in sample
    assert "tournament_name" in sample
    assert "player1_name" in sample
    assert "player2_name" in sample
    assert "status" in sample


def test_unified_matches_platform_filter():
    res = client.get("/api/all/matches?platform=league_pro&date_from=2026-09-18&date_to=2026-09-19")
    assert res.status_code == 200
    data = res.json()
    for m in data["matches"]:
        assert m["platform"] == "league_pro"
