import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

from league_pro_scraper import LeagueProScraper
from sport_liga_scraper import SportLigaScraper


class TestTTParser(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_01_api_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "online")

    def test_02_league_pro_scraper(self):
        async def run():
            scraper = LeagueProScraper()
            try:
                tournaments = await scraper.get_tournaments("2026-09-18", "2026-09-19")
                self.assertIsInstance(tournaments, list)
                self.assertGreater(len(tournaments), 0)

                matches_res = await scraper.get_matches("2026-09-18", "2026-09-19")
                self.assertGreater(matches_res.total, 0)
                self.assertIn("all", matches_res.counts)
                self.assertIn("live", matches_res.counts)
            finally:
                await scraper.close()
        asyncio.run(run())

    def test_03_sport_liga_scraper(self):
        async def run():
            scraper = SportLigaScraper()
            try:
                tournaments = await scraper.get_tournaments("2026-09-18", "2026-09-19")
                self.assertIsInstance(tournaments, list)
                self.assertGreater(len(tournaments), 0)

                matches_res = await scraper.get_matches("2026-09-18", "2026-09-19")
                self.assertGreater(matches_res.total, 0)
                self.assertIn("all", matches_res.counts)
                self.assertIn("live", matches_res.counts)
            finally:
                await scraper.close()
        asyncio.run(run())

    def test_04_leaguepro_api_endpoints(self):
        res_t = self.client.get("/api/leaguepro/tournaments?date_from=2026-09-18&date_to=2026-09-19")
        self.assertEqual(res_t.status_code, 200)
        self.assertGreater(len(res_t.json()), 0)

        res_m = self.client.get("/api/leaguepro/matches?date_from=2026-09-18&date_to=2026-09-19")
        self.assertEqual(res_m.status_code, 200)
        self.assertGreater(res_m.json()["total"], 0)

    def test_05_sportliga_api_endpoints(self):
        res_t = self.client.get("/api/sportliga/tournaments?date_from=2026-09-18&date_to=2026-09-19")
        self.assertEqual(res_t.status_code, 200)
        self.assertGreater(len(res_t.json()), 0)

        res_m = self.client.get("/api/sportliga/matches?date_from=2026-09-18&date_to=2026-09-19")
        self.assertEqual(res_m.status_code, 200)
        self.assertGreater(res_m.json()["total"], 0)

    def test_06_unified_matches_endpoint(self):
        res = self.client.get("/api/all/matches?date_from=2026-09-18&date_to=2026-09-19")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(data["total"], 0)
        self.assertIn("platform_counts", data)
        self.assertIn("league_pro", data["platform_counts"])
        self.assertIn("sport_liga", data["platform_counts"])
        self.assertIn("setka", data["platform_counts"])
        self.assertIn("ttcup", data["platform_counts"])

        # Check sample item
        first = data["matches"][0]
        self.assertIn("id", first)
        self.assertIn("platform", first)
        self.assertIn("tournament_name", first)
        self.assertIn("status", first)
        self.assertIn("time", first)

    def test_07_unified_matches_platform_filter(self):
        res = self.client.get("/api/all/matches?platform=sport_liga&date_from=2026-09-18&date_to=2026-09-18")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        for m in data["matches"]:
            self.assertEqual(m["platform"], "sport_liga")
            self.assertEqual(m["platform_name"], "Liga Pro")

    def test_08_ligapro_api_aliases(self):
        res_t = self.client.get("/api/ligapro/tournaments?date_from=2026-09-18&date_to=2026-09-18")
        self.assertEqual(res_t.status_code, 200)
        self.assertGreater(len(res_t.json()), 0)

        res_m = self.client.get("/api/ligapro/matches?date_from=2026-09-18&date_to=2026-09-18")
        self.assertEqual(res_m.status_code, 200)
        self.assertGreater(res_m.json()["total"], 0)

    def test_09_country_and_city_detection(self):
        # Belarus
        c, code, city = SportLigaScraper.detect_country_and_city("Tournament A15. League 400-450")
        self.assertEqual(c, "Belarus")
        self.assertEqual(code, "by")
        self.assertEqual(city, "Minsk")

        c, code, city = SportLigaScraper.detect_country_and_city("Minsk Open 2026")
        self.assertEqual(c, "Belarus")
        self.assertEqual(code, "by")
        self.assertEqual(city, "Minsk")

        # Moldova
        c, code, city = SportLigaScraper.detect_country_and_city("Tournament Moldova Chisinau Cup")
        self.assertEqual(c, "Moldova")
        self.assertEqual(code, "md")
        self.assertEqual(city, "Chisinau")

        # Russia - Moscow & other cities
        c, code, city = SportLigaScraper.detect_country_and_city("Tournament A5. League 250-300")
        self.assertEqual(c, "Russia")
        self.assertEqual(code, "ru")
        self.assertEqual(city, "Moscow")

        c, code, city = SportLigaScraper.detect_country_and_city("Balashikha League Pro 2026")
        self.assertEqual(c, "Russia")
        self.assertEqual(code, "ru")
        self.assertEqual(city, "Balashikha")

        c, code, city = SportLigaScraper.detect_country_and_city("Tournament Saint Petersburg SPB Cup")
        self.assertEqual(c, "Russia")
        self.assertEqual(code, "ru")
        self.assertEqual(city, "Saint Petersburg")

    def test_10_unified_platform_ligapro_branding(self):
        res = self.client.get("/api/all/matches?platform=liga_pro&date_from=2026-09-18&date_to=2026-09-18")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("liga_pro", data["platform_counts"])
        self.assertGreater(data["platform_counts"]["liga_pro"], 0)
        for m in data["matches"]:
            self.assertEqual(m["platform_name"], "Liga Pro")
            self.assertIn(m["country_code"], ["ru", "by", "md"])

    def test_11_ttcup_config_and_cookie(self):
        # 1. Update cookie
        test_cookie = "PHPSESSID=unit_test_session_12345; cf_clearance=unit_test_clearance"
        res_post = self.client.post("/api/ttcup/config", json={"cookie": test_cookie})
        self.assertEqual(res_post.status_code, 200)
        data_post = res_post.json()
        self.assertTrue(data_post["cookie_set"])

        # 2. Get cookie status
        res_get = self.client.get("/api/ttcup/config")
        self.assertEqual(res_get.status_code, 200)
        data_get = res_get.json()
        self.assertTrue(data_get["cookie_set"])
        self.assertIsNotNone(data_get["cookie_snippet"])

    def test_12_ttcup_deduplication_and_just_finished(self):
        # Test unified matches response includes just_finished count
        res = self.client.get("/api/all/matches?date_from=2026-09-18&date_to=2026-09-18")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("just_finished", data["counts"])

        # Verify no duplicate TT Cup matches
        ttcup_matches = [m for m in data["matches"] if m["platform"] == "ttcup"]
        seen_keys = set()
        for m in ttcup_matches:
            pair = "_vs_".join(sorted([m["player1_name"].lower(), m["player2_name"].lower()]))
            key = f"{m['start_date'] or m['time']}_{pair}"
            self.assertNotIn(key, seen_keys, f"Found duplicate TT Cup match: {key}")
            seen_keys.add(key)


if __name__ == "__main__":
    unittest.main()

