import json
from fastapi.testclient import TestClient
from main import app, match_cache_manager

client = TestClient(app)

def test_endpoints():
    print("Testing GET /api/ttcup/config...")
    r = client.get("/api/ttcup/config")
    assert r.status_code == 200, f"Status: {r.status_code}"
    data = r.json()
    print("Config response:", data)
    assert data["cookie_set"] is True
    assert "csrftoken" in data["cookie_names"]

    print("Testing POST /api/ttcup/config with JSON array...")
    cookie_sample = [
        {
            "domain": "ttcup.com",
            "expirationDate": 1821154768.018189,
            "hostOnly": True,
            "httpOnly": False,
            "name": "csrftoken",
            "path": "/",
            "sameSite": "lax",
            "secure": False,
            "session": False,
            "storeId": None,
            "value": "sample_csrf_test_value"
        },
        {
            "domain": "ttcup.com",
            "name": "sessionid",
            "value": "sample_session_test_value"
        }
    ]
    r = client.post("/api/ttcup/config", json={"cookie": cookie_sample})
    assert r.status_code == 200
    data = r.json()
    print("Updated config response:", data)
    assert data["cookies_count"] == 2
    assert "csrftoken" in data["cookie_names"] and "sessionid" in data["cookie_names"]

    # Restore original cookie
    with open("ttcup_cookie.txt", "r", encoding="utf-8") as f:
        orig = json.load(f)
    r = client.post("/api/ttcup/config", json={"cookie": orig})
    assert r.status_code == 200

    print("Testing GET /api/removed-matches...")
    r = client.get("/api/removed-matches")
    assert r.status_code == 200
    data = r.json()
    print(f"Removed matches total: {data['total']}")

    print("Testing MatchCacheManager removed matches flow...")
    from models import UnifiedMatchItem
    test_match = UnifiedMatchItem(
        id="test_m_101",
        platform="ttcup",
        platform_name="TT Cup",
        tournament_name="Test Tournament",
        player1_name="Ivan Test",
        player2_name="Petr Test",
        status="upcoming",
        start_date="2026-09-18T10:00:00",
        time="10:00",
        score="-"
    )
    # 1. Process match
    match_cache_manager.process_matches([test_match], date_from="2026-09-18", date_to="2026-09-18", platform_filter="ttcup")
    
    # 2. Simulate disappearance: missing in refresh
    active = match_cache_manager.process_matches([], date_from="2026-09-18", date_to="2026-09-18", platform_filter="ttcup")
    assert any(m.id == "test_m_101" for m in active), "Match should stay in cache during grace period!"
    print("Match correctly retained in cache during disappearance!")

    # 3. Fast-forward time to simulate expiration > 300s
    item = match_cache_manager._cache["test_m_101"]
    item["last_seen_at"] -= 305  # > 300s
    active = match_cache_manager.process_matches([], date_from="2026-09-18", date_to="2026-09-18", platform_filter="ttcup")
    assert not any(m.id == "test_m_101" for m in active), "Match should be expired after 5 min!"
    
    # 4. Check removed endpoint
    r = client.get("/api/removed-matches")
    data = r.json()
    removed_ids = [m["id"] for m in data["matches"]]
    assert "test_m_101" in removed_ids
    print("Match successfully found in /api/removed-matches!")

    # 5. Restore match
    r = client.post("/api/removed-matches/restore/test_m_101")
    assert r.status_code == 200
    print("Match restore API OK!")

    # 6. Clear removed matches
    r = client.post("/api/removed-matches/clear")
    assert r.status_code == 200
    r = client.get("/api/removed-matches")
    assert r.json()["total"] == 0
    print("Clear removed matches API OK!")

    print("\nALL BACKEND TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_endpoints()
