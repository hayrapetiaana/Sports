import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

def test_esports_page():
    res = client.get("/esports")
    assert res.status_code == 200
    assert "ESPORTSPARSER" in res.text or "Esports Matches Monitor" in res.text
    assert '<link rel="icon"' in res.text
    print("[PASS] /esports page served with favicon")

def test_disciplines_endpoint():
    res = client.get("/api/esports/disciplines")
    assert res.status_code == 200
    data = res.json()
    assert "disciplines" in data
    assert len(data["disciplines"]) == 27
    print(f"[PASS] /api/esports/disciplines returns {len(data['disciplines'])} disciplines")

def test_removed_matches_endpoint():
    res = client.get("/api/esports/removed-matches")
    assert res.status_code == 200
    data = res.json()
    assert "matches" in data
    print("[PASS] /api/esports/removed-matches endpoint works")

if __name__ == "__main__":
    test_esports_page()
    test_disciplines_endpoint()
    test_removed_matches_endpoint()
    print("\nALL FASTAPI ESPORTS TESTS PASSED!")
