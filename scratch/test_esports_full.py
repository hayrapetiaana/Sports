import sys
import os
import asyncio
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from liquipedia_scraper import LiquipediaScraper, DISCIPLINES
from hltv_scraper import HLTVScraper
from models import EsportsMatchItem

async def run_tests():
    print("=== TEST 1: Disciplines Definition ===")
    print(f"Total supported disciplines: {len(DISCIPLINES)}")
    assert len(DISCIPLINES) >= 27, f"Expected at least 27 disciplines, got {len(DISCIPLINES)}"
    print("Discipline samples:", list(DISCIPLINES.keys())[:5])

    print("\n=== TEST 2: Liquipedia Scraper (Dota 2) ===")
    lp = LiquipediaScraper()
    dota_matches = await lp.scrape_matches("dota2")
    print(f"Scraped {len(dota_matches)} Dota 2 matches")
    if dota_matches:
        sample = dota_matches[0]
        print(f"Sample match: [{sample.discipline_name}] {sample.team1_name} ({sample.team1_short}) vs {sample.team2_name} ({sample.team2_short})")
        print(f"Format: {sample.format}, Status: {sample.status}, Tournament: {sample.tournament}")
        print(f"Streams: {[s.dict() for s in sample.streams]}")
        assert sample.team1_name, "team1_name should not be empty"
        assert sample.team2_name, "team2_name should not be empty"
        assert sample.format, "format should be present"

    print("\n=== TEST 3: Liquipedia Scraper (Counter-Strike) ===")
    cs_matches = await lp.scrape_matches("counterstrike")
    print(f"Scraped {len(cs_matches)} CS matches")
    if cs_matches:
        sample = cs_matches[0]
        print(f"Sample CS: {sample.team1_name} vs {sample.team2_name} | Format: {sample.format}")

    print("\n=== TEST 4: HLTV Scraper & Merger ===")
    hltv = HLTVScraper()
    today_str = datetime.now().strftime("%Y-%m-%d")
    hltv_matches = await hltv.get_matches(today_str)
    print(f"Scraped {len(hltv_matches)} matches from HLTV for {today_str}")
    merged_cs = hltv.merge_with_liquipedia(cs_matches, hltv_matches)
    print(f"CS matches after HLTV merge: {len(merged_cs)} (original was {len(cs_matches)})")

    print("\n=== TEST 5: FastAPI Application Endpoints Check ===")
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)

    # 1. Test GET /esports
    resp = client.get("/esports")
    print(f"GET /esports status: {resp.status_code}")
    assert resp.status_code == 200
    assert "ESPORTS" in resp.text

    # 2. Test GET /api/esports/disciplines
    resp = client.get("/api/esports/disciplines")
    print(f"GET /api/esports/disciplines status: {resp.status_code}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data.get("disciplines", [])) >= 27

    # 3. Test GET /api/esports/matches?discipline=dota2
    resp = client.get("/api/esports/matches?discipline=dota2")
    print(f"GET /api/esports/matches?discipline=dota2 status: {resp.status_code}")
    assert resp.status_code == 200
    m_data = resp.json()
    print(f"Returned matches: {len(m_data.get('matches', []))}")

    # 4. Test GET /api/esports/removed-matches
    resp = client.get("/api/esports/removed-matches")
    print(f"GET /api/esports/removed-matches status: {resp.status_code}")
    assert resp.status_code == 200

    # 5. Test GET /api/hltv/config
    resp = client.get("/api/hltv/config")
    print(f"GET /api/hltv/config status: {resp.status_code}")
    assert resp.status_code == 200

    # 6. Test GET /api/liquipedia/config
    resp = client.get("/api/liquipedia/config")
    print(f"GET /api/liquipedia/config status: {resp.status_code}")
    assert resp.status_code == 200

    print("\nALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_tests())
