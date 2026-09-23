import asyncio
import datetime
import logging
from typing import Dict, List, Optional, Any
import httpx

from models import (
    LeagueProPlayer,
    LeagueProTournament,
    LeagueProMatch,
    LeagueProMatchesResponse,
)

logger = logging.getLogger("league_pro_scraper")

BASE_API_URL = "https://api.league-pro.com"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://tt.league-pro.com",
    "Referer": "https://tt.league-pro.com/",
}


class LeagueProCacheEntry:
    def __init__(self, data: Any, timestamp: float):
        self.data = data
        self.timestamp = timestamp

    def is_valid(self, ttl: float) -> bool:
        return (datetime.datetime.now().timestamp() - self.timestamp) < ttl


class LeagueProScraper:
    def __init__(self, cache_ttl: float = 30.0, max_concurrency: int = 8):
        self.cache_ttl = cache_ttl
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self._client: Optional[httpx.AsyncClient] = None
        self._client_loop: Optional[asyncio.AbstractEventLoop] = None

        self._tournaments_cache: Dict[str, LeagueProCacheEntry] = {}
        self._matches_cache: Dict[str, LeagueProCacheEntry] = {}

    async def get_client(self) -> httpx.AsyncClient:
        current_loop = asyncio.get_running_loop()
        if (
            self._client is None
            or self._client.is_closed
            or self._client_loop != current_loop
        ):
            self._client = httpx.AsyncClient(
                headers=DEFAULT_HEADERS,
                timeout=httpx.Timeout(20.0, connect=10.0),
                follow_redirects=True,
                verify=False,
            )
            self._client_loop = current_loop
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
            self._client_loop = None

    @staticmethod
    def _parse_player(p_data: Optional[Dict[str, Any]]) -> LeagueProPlayer:
        if not p_data:
            return LeagueProPlayer(name="TBA", short_name="TBA")
        p = p_data.get("player") or {}
        first_name = p.get("first_name_en") or ""
        surname = p.get("surname_en") or ""
        full_name = f"{first_name} {surname}".strip() or "TBA"
        short_name = p.get("short_name_en") or surname or full_name
        avatar = p.get("avatar") or p.get("photo")
        rating = p_data.get("rating_before_tournament")
        return LeagueProPlayer(
            id=p.get("id"),
            name=full_name,
            short_name=short_name,
            avatar=avatar,
            rating=float(rating) if rating is not None else None,
        )

    async def get_tournaments(
        self, date_from: str, date_to: str
    ) -> List[LeagueProTournament]:
        cache_key = f"{date_from}_{date_to}"
        if cache_key in self._tournaments_cache:
            entry = self._tournaments_cache[cache_key]
            if entry.is_valid(self.cache_ttl):
                return entry.data

        client = await self.get_client()
        tournaments: List[LeagueProTournament] = []
        limit = 100
        offset = 0

        while True:
            url = f"{BASE_API_URL}/tournaments?date_from={date_from}&date_to={date_to}&limit={limit}&offset={offset}"
            try:
                async with self.semaphore:
                    resp = await client.get(url)
                if resp.status_code != 200:
                    logger.error(
                        "League Pro API error for tournaments %s: %s", url, resp.status_code
                    )
                    break
                data = resp.json()
                items = data.get("items", [])
                pagination = data.get("pagination", {})
                total_items = pagination.get("total_items", 0)

                for item in items:
                    sides = item.get("sides", [])
                    players = [self._parse_player(s) for s in sides]
                    t = LeagueProTournament(
                        id=item.get("id"),
                        name=item.get("name_en") or f"Tournament {item.get('id')}",
                        start_at=item.get("start_at", ""),
                        status=item.get("status", 1),
                        sides_count=item.get("sides_count"),
                        players=players,
                    )
                    tournaments.append(t)

                offset += len(items)
                if offset >= total_items or len(items) == 0:
                    break
            except Exception as e:
                logger.error("Error fetching League Pro tournaments: %s", e)
                break

        self._tournaments_cache[cache_key] = LeagueProCacheEntry(
            tournaments, datetime.datetime.now().timestamp()
        )
        return tournaments

    async def get_matches(
        self,
        date_from: str,
        date_to: str,
        tournament_filter: Optional[int] = None,
        status_filter: Optional[str] = "all",
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        search: Optional[str] = None,
    ) -> LeagueProMatchesResponse:
        cache_key = f"{date_from}_{date_to}"
        raw_matches: List[LeagueProMatch] = []
        is_cached = False
        cache_age = 0.0

        if cache_key in self._matches_cache:
            entry = self._matches_cache[cache_key]
            if entry.is_valid(self.cache_ttl):
                raw_matches = entry.data
                is_cached = True
                cache_age = datetime.datetime.now().timestamp() - entry.timestamp

        tournaments = await self.get_tournaments(date_from, date_to)

        if not is_cached:
            client = await self.get_client()
            limit = 100
            offset = 0

            while True:
                url = f"{BASE_API_URL}/matches?date_from={date_from}&date_to={date_to}&limit={limit}&offset={offset}"
                try:
                    async with self.semaphore:
                        resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.error("League Pro matches error: %s", resp.status_code)
                        break
                    data = resp.json()
                    items = data.get("items", [])
                    pagination = data.get("pagination", {})
                    total_items = pagination.get("total_items", 0)

                    for item in items:
                        t_info = item.get("tournament") or {}
                        t_id = t_info.get("id") or 0
                        t_name = t_info.get("name_en") or f"Tournament {t_id}"

                        stage_info = item.get("stage") or {}
                        stage_name = stage_info.get("name_en") or "Group Stage"

                        start_date_str = item.get("start_date") or ""
                        time_str = "--:--"
                        if start_date_str:
                            try:
                                # Parse ISO UTC time (e.g. 2026-09-18T22:00:00Z)
                                dt = datetime.datetime.fromisoformat(
                                    start_date_str.replace("Z", "+00:00")
                                )
                                time_str = dt.strftime("%H:%M")
                            except Exception:
                                pass

                        p1 = self._parse_player(item.get("side_one"))
                        p2 = self._parse_player(item.get("side_two"))

                        results = item.get("results") or {}
                        s1 = results.get("score_one")
                        s2 = results.get("score_two")
                        score_str = f"{s1}:{s2}" if s1 is not None and s2 is not None else "-"

                        # Set scores
                        periods = results.get("period_scores") or []
                        period_strs = []
                        for p in periods:
                            if isinstance(p, dict):
                                ps1 = p.get("score_one")
                                ps2 = p.get("score_two")
                                if ps1 is not None and ps2 is not None:
                                    period_strs.append(f"{ps1}:{ps2}")
                        set_scores_str = ", ".join(period_strs) if period_strs else None

                        raw_st = item.get("status", 1)
                        if raw_st == 2:
                            match_status = "live"
                        elif raw_st == 3 or (s1 is not None and s2 is not None and (s1 >= 3 or s2 >= 3)):
                            match_status = "finished"
                        else:
                            match_status = "upcoming"

                        raw_matches.append(
                            LeagueProMatch(
                                id=item.get("id"),
                                tournament_id=t_id,
                                tournament_name=t_name,
                                stage=stage_name,
                                start_date=start_date_str,
                                time=time_str,
                                player1=p1,
                                player2=p2,
                                score=score_str,
                                set_scores=set_scores_str,
                                status=match_status,
                                raw_status=raw_st,
                            )
                        )

                    offset += len(items)
                    if offset >= total_items or len(items) == 0:
                        break
                except Exception as e:
                    logger.error("Error fetching League Pro matches: %s", e)
                    break

            self._matches_cache[cache_key] = LeagueProCacheEntry(
                raw_matches, datetime.datetime.now().timestamp()
            )

        # Sort matches by start_date / time
        raw_matches.sort(key=lambda m: (m.start_date, m.time))

        # Filtering
        filtered = list(raw_matches)

        if tournament_filter:
            filtered = [m for m in filtered if m.tournament_id == tournament_filter]

        if status_filter and status_filter != "all":
            filtered = [m for m in filtered if m.status == status_filter]

        if from_time or to_time:
            time_filtered = []
            for m in filtered:
                m_time = m.time
                if m_time == "--:--":
                    time_filtered.append(m)
                    continue
                if from_time and m_time < from_time:
                    continue
                if to_time and m_time > to_time:
                    continue
                time_filtered.append(m)
            filtered = time_filtered

        if search:
            q = search.lower().strip()
            filtered = [
                m
                for m in filtered
                if q in m.player1.name.lower()
                or q in (m.player1.short_name or "").lower()
                or q in m.player2.name.lower()
                or q in (m.player2.short_name or "").lower()
                or q in m.tournament_name.lower()
                or q in m.stage.lower()
            ]

        counts = {
            "all": len(raw_matches),
            "live": sum(1 for m in raw_matches if m.status == "live"),
            "upcoming": sum(1 for m in raw_matches if m.status == "upcoming"),
            "finished": sum(1 for m in raw_matches if m.status == "finished"),
        }

        return LeagueProMatchesResponse(
            total=len(filtered),
            counts=counts,
            date_from=date_from,
            date_to=date_to,
            tournament_filter=tournament_filter,
            status_filter=status_filter,
            from_time=from_time,
            to_time=to_time,
            search=search,
            cached=is_cached,
            cache_age_seconds=cache_age if is_cached else None,
            tournaments=tournaments,
            matches=filtered,
        )
