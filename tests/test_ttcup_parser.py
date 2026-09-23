import os
import sys
import unittest
from bs4 import BeautifulSoup

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ttcup_scraper import TTCupScraper
from models import TTCupTournament

class TestTTCupParser(unittest.TestCase):
    def setUp(self):
        self.scraper = TTCupScraper()

    def test_normalize_date(self):
        tt_date, iso_date = self.scraper.normalize_date("2026-09-17")
        self.assertEqual(tt_date, "17.09.2026")
        self.assertEqual(iso_date, "2026-09-17")

        tt_date2, iso_date2 = self.scraper.normalize_date("17.09.2026")
        self.assertEqual(tt_date2, "17.09.2026")
        self.assertEqual(iso_date2, "2026-09-17")

    def test_parse_tournaments_from_saved_html(self):
        path = r"C:\Users\hayra\.gemini\antigravity-ide\brain\b73fd56f-8188-4522-9d21-90b17357b352\.system_generated\steps\17\content.md"
        if not os.path.exists(path):
            self.skipTest("Saved step 17 HTML not found")

        with open(path, "r", encoding="utf-8") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")
        tournaments = self.scraper._parse_tournaments_from_soup(soup, "17.09.2026")
        self.assertGreater(len(tournaments), 10)

        # Check Czech Republic and Poland presence
        czech = [t for t in tournaments if t.country_code == "cz"]
        poland = [t for t in tournaments if t.country_code == "pl"]
        self.assertGreater(len(czech), 0)
        self.assertGreater(len(poland), 0)

        # Verify hall IDs
        hall_ids = [t.hall_id for t in tournaments]
        self.assertIn(9, hall_ids)
        self.assertIn(3, hall_ids)
        self.assertIn(22, hall_ids)

        # Verify specific Poland tournament
        poland_3 = next((t for t in tournaments if t.hall_id == 3), None)
        self.assertIsNotNone(poland_3)
        self.assertEqual(poland_3.country, "Poland")
        self.assertEqual(poland_3.name, "Poland 1")

        # Verify specific Czech tournament
        czech_9 = next((t for t in tournaments if t.hall_id == 9), None)
        self.assertIsNotNone(czech_9)
        self.assertEqual(czech_9.country, "Czech Republic")
        self.assertEqual(czech_9.name, "Czech 8")

    def test_parse_schedule_detail_from_saved_html(self):
        path = r"C:\Users\hayra\.gemini\antigravity-ide\brain\b73fd56f-8188-4522-9d21-90b17357b352\.system_generated\steps\61\content.md"
        if not os.path.exists(path):
            self.skipTest("Saved step 61 HTML not found")

        with open(path, "r", encoding="utf-8") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")
        tourn = TTCupTournament(
            hall_id=9,
            name="Czech 8",
            country="Czech Republic",
            country_code="cz",
            date="17.09.2026",
            url="/schedule/17.09.2026/h:9/",
            full_url="https://ttcup.com/schedule/17.09.2026/h:9/"
        )
        detail = self.scraper._parse_schedule_detail_from_soup(soup, tourn, "17.09.2026")
        self.assertEqual(len(detail.matches), 6)

        m1 = detail.matches[0]
        self.assertEqual(m1.order, 1)
        self.assertEqual(m1.time, "20:55")
        self.assertEqual(m1.player1_name, "Vorisek Tomas")
        self.assertEqual(m1.player2_name, "Stusek Martin")
        self.assertEqual(m1.hall_id, 9)

        # Standings table
        self.assertEqual(len(detail.standings), 4)
        self.assertEqual(detail.standings[0].player_name, "Vorisek Tomas")

    def test_filter_timeframe_and_country(self):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Test sample data retrieval and filtering
        res = loop.run_until_complete(
            self.scraper.get_matches(
                date="17.09.2026",
                country="poland",
                from_time="13:00",
                to_time="15:00",
            )
        )
        self.assertEqual(res.country_filter, "poland")
        for m in res.matches:
            self.assertEqual(m.country, "Poland")
            self.assertTrue("13:00" <= m.time <= "15:00")

        # Test Czech Republic
        res_cz = loop.run_until_complete(
            self.scraper.get_matches(
                date="17.09.2026",
                country="czech",
                from_time="18:00",
                to_time="20:00",
            )
        )
        self.assertEqual(res_cz.country_filter, "czech")
        for m in res_cz.matches:
            self.assertEqual(m.country, "Czech Republic")
            self.assertTrue("18:00" <= m.time <= "20:00")
        
        loop.close()

if __name__ == "__main__":
    unittest.main()
