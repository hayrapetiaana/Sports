import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
import main

class TestFastAPITTCupEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_health_endpoint(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("tt_cup", data.get("services", {}))

    def test_ttcup_status_endpoint(self):
        res = self.client.get("/api/ttcup/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "online")

    def test_ttcup_tournaments_endpoint(self):
        res = self.client.get("/api/ttcup/tournaments?date=17.09.2026")
        self.assertEqual(res.status_code, 200)
        tournaments = res.json()
        self.assertIsInstance(tournaments, list)
        self.assertGreater(len(tournaments), 0)

        # Check country filtering
        res_cz = self.client.get("/api/ttcup/tournaments?date=17.09.2026&country=czech")
        self.assertEqual(res_cz.status_code, 200)
        for t in res_cz.json():
            self.assertEqual(t["country_code"], "cz")

        res_pl = self.client.get("/api/ttcup/tournaments?date=17.09.2026&country=poland")
        self.assertEqual(res_pl.status_code, 200)
        for t in res_pl.json():
            self.assertEqual(t["country_code"], "pl")

    def test_ttcup_schedule_endpoint(self):
        res = self.client.get("/api/ttcup/schedule?hall=9&date=17.09.2026")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["tournament"]["hall_id"], 9)
        self.assertGreater(len(data["matches"]), 0)

    def test_ttcup_matches_timeframe_filter_endpoint(self):
        res = self.client.get("/api/ttcup/matches?date=17.09.2026&country=czech&from_time=18:00&to_time=20:00")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total", data)
        self.assertIn("matches", data)
        for m in data["matches"]:
            self.assertEqual(m["country"], "Czech Republic")
            self.assertTrue("18:00" <= m["time"] <= "20:00")

    def test_ttcup_config_endpoint(self):
        res = self.client.post("/api/ttcup/config", json={"cookie": "test_cookie=123"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("cookie_set"))

    def test_index_html_served(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("TT CUP", res.text)
        self.assertIn("section-ttcup", res.text)
        self.assertIn("ttcup.com/schedule/", res.text)

if __name__ == "__main__":
    unittest.main()
