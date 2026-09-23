import pytest
import pytest_asyncio
from sport_liga_scraper import SportLigaScraper


@pytest.mark.asyncio
async def test_sport_liga_tournaments():
    scraper = SportLigaScraper()
    try:
        tournaments = await scraper.get_tournaments("2026-09-18", "2026-09-19")
        assert isinstance(tournaments, list)
        assert len(tournaments) > 0
        first = tournaments[0]
        assert first.id > 0
        assert first.name
        assert first.start_at
    finally:
        await scraper.close()


@pytest.mark.asyncio
async def test_sport_liga_matches():
    scraper = SportLigaScraper()
    try:
        res = await scraper.get_matches("2026-09-18", "2026-09-19")
        assert res.total > 0
        assert len(res.matches) == res.total
        assert "all" in res.counts
        assert "live" in res.counts
        assert "upcoming" in res.counts
        assert "finished" in res.counts

        first_match = res.matches[0]
        assert first_match.id > 0
        assert first_match.tournament_id > 0
        assert first_match.tournament_name
        assert first_match.player1.name
        assert first_match.player2.name
        assert first_match.status in ("upcoming", "live", "finished")
    finally:
        await scraper.close()
