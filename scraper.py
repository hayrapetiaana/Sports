import asyncio
import base64
import datetime
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
import httpx
from bs4 import BeautifulSoup

from models import (
    HallInfo,
    MatchItem,
    MatchesResponse,
    PeriodInfo,
    Player,
    ScoreSets,
    SetScore,
)

logger = logging.getLogger("tt_scraper")
logging.basicConfig(level=logging.INFO)

BASE_URL = "https://tabletennis.setkacup.com"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_PERIOD_NAMES = {
    1: "Утро",
    2: "Вечер",
    3: "Ночь",
    4: "День 1",
    5: "День 2",
    6: "Ночь 1",
    7: "Полуночь",
}


class CacheEntry:
    def __init__(self, data: List[MatchItem], timestamp: float):
        self.data = data
        self.timestamp = timestamp

    def is_valid(self, ttl: float) -> bool:
        return (datetime.datetime.now().timestamp() - self.timestamp) < ttl


class SetkaCupScraper:
    def __init__(self, cache_ttl: float = 30.0, max_concurrency: int = 10):
        self.cache_ttl = cache_ttl
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self._cache: Dict[str, CacheEntry] = {}
        self._halls_map: Dict[int, HallInfo] = {}
        self._periods_map: Dict[int, PeriodInfo] = {}
        self._metadata_loaded = False
        self._lock = asyncio.Lock()

        # Shared HTTP client configuration
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                headers={
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "ru,en-US;q=0.9,en;q=0.8",
                    "Referer": f"{BASE_URL}/",
                },
                timeout=httpx.Timeout(12.0, connect=6.0),
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def load_metadata(self, force: bool = False):
        if self._metadata_loaded and not force:
            return

        async with self._lock:
            if self._metadata_loaded and not force:
                return

            client = await self.get_client()

            # Load Halls / Locations
            try:
                resp = await client.get("/api/Locations/ru")
                if resp.status_code == 200:
                    locations = resp.json()
                    for loc in locations:
                        lid = loc.get("id")
                        if lid:
                            self._halls_map[int(lid)] = HallInfo(
                                id=int(lid),
                                name=loc.get("name") or f"Зал {lid}",
                                color=loc.get("color"),
                                official=loc.get("official"),
                                stream_url=loc.get("streamPublic") or loc.get("channel"),
                            )
                    logger.info("Loaded %d halls from Setka Cup API", len(self._halls_map))
            except Exception as e:
                logger.warning("Failed to fetch /api/Locations/ru: %s", e)

            # Load DayPeriods
            try:
                resp = await client.get("/api/DayPeriods/ru")
                if resp.status_code == 200:
                    periods = resp.json()
                    for p in periods:
                        pid = p.get("id")
                        if pid:
                            self._periods_map[int(pid)] = PeriodInfo(
                                id=int(pid),
                                name=p.get("name") or DEFAULT_PERIOD_NAMES.get(int(pid), f"Период {pid}"),
                            )
                    logger.info("Loaded %d periods from Setka Cup API", len(self._periods_map))
            except Exception as e:
                logger.warning("Failed to fetch /api/DayPeriods/ru: %s", e)

            self._metadata_loaded = True

    def get_hall_info(self, hall_id: Optional[int]) -> HallInfo:
        hid = int(hall_id or 0)
        if hid in self._halls_map:
            return self._halls_map[hid]
        return HallInfo(id=hid, name=f"Зал {hid}" if hid > 0 else "Не указан")

    def get_period_info(self, period_id: Optional[int]) -> PeriodInfo:
        pid = int(period_id or 0)
        if pid in self._periods_map:
            return self._periods_map[pid]
        name = DEFAULT_PERIOD_NAMES.get(pid, f"Период {pid}" if pid > 0 else "Общий")
        return PeriodInfo(id=pid, name=name)

    def _get_photo_url(self, photo_token: Optional[str]) -> Optional[str]:
        """Return local backend proxy URL for player photo if token exists."""
        if not photo_token:
            return None
        token = str(photo_token).strip()
        if not token or token == "-":
            return None
        return f"/api/player-photo/{token}"

    async def fetch_player_photo(self, photo_token: str) -> Optional[bytes]:
        """Fetch player photo from Setka Cup API using browser headers."""
        if not photo_token or photo_token == "-":
            return None
        client = await self.get_client()
        url = f"/api/Image/setka/90x90/{photo_token}.jpeg"
        try:
            async with self.semaphore:
                resp = await client.get(url)
                if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                    return resp.content
        except Exception as e:
            logger.debug("Failed to fetch player photo for token %s: %s", photo_token, e)
        return None

    def _format_time(self, iso_str: Optional[str]) -> Tuple[str, Optional[str]]:
        if not iso_str:
            return "--:--", None
        try:
            # Format: "2026-09-16T19:45:00.000Z"
            dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            # Display time as HH:MM UTC or local
            formatted = dt.strftime("%H:%M")
            return formatted, iso_str
        except Exception:
            return iso_str[:16].split("T")[-1] if "T" in str(iso_str) else str(iso_str), iso_str

    def _parse_match_obj(
        self,
        m: Dict[str, Any],
        live_widgets_map: Dict[int, Dict[str, Any]],
        default_location_id: Optional[int] = None,
        default_period_id: Optional[int] = None,
    ) -> MatchItem:
        match_id = int(m.get("id") or m.get("matchId") or 0)
        tournament_id = m.get("tournamentId")
        tournament_name = m.get("tournamentName")
        position = m.get("position")
        stage = tournament_name or (f"Матч #{position}" if position else "Групповой этап")

        location_id = m.get("locationId") or default_location_id
        period_id = m.get("dayPeriodToken") or default_period_id

        hall = self.get_hall_info(location_id)
        period = self.get_period_info(period_id)

        # Live widget match override if active
        live_match = live_widgets_map.get(match_id)
        active_player_id = None
        if live_match:
            active_player_id = live_match.get("activePlayerId")

        # Player 1
        p1_raw = m.get("player1") or {}
        p1_first = p1_raw.get("firstName") or m.get("player1FirstName") or ""
        p1_last = p1_raw.get("lastName") or m.get("player1LastName") or ""
        p1_name = f"{p1_first} {p1_last}".strip() or "Игрок 1"
        p1_id = p1_raw.get("id") or m.get("player1Id")
        p1_photo = self._get_photo_url(p1_raw.get("photo") or m.get("player1Photo"))
        p1_color = p1_raw.get("player1ColorId") or m.get("player1ColorId")

        # Player 2
        p2_raw = m.get("player2") or {}
        p2_first = p2_raw.get("firstName") or m.get("player2FirstName") or ""
        p2_last = p2_raw.get("lastName") or m.get("player2LastName") or ""
        p2_name = f"{p2_first} {p2_last}".strip() or "Игрок 2"
        p2_id = p2_raw.get("id") or m.get("player2Id")
        p2_photo = self._get_photo_url(p2_raw.get("photo") or m.get("player2Photo"))
        p2_color = p2_raw.get("player2ColorId") or m.get("player2ColorId")

        is_p1_serving = bool(active_player_id and p1_id and int(active_player_id) == int(p1_id))
        is_p2_serving = bool(active_player_id and p2_id and int(active_player_id) == int(p2_id))

        player1 = Player(
            id=p1_id,
            name=p1_name,
            first_name=p1_first,
            last_name=p1_last,
            gender=p1_raw.get("gender"),
            photo_url=p1_photo,
            color_id=p1_color,
            is_serving=is_p1_serving,
        )

        player2 = Player(
            id=p2_id,
            name=p2_name,
            first_name=p2_first,
            last_name=p2_last,
            gender=p2_raw.get("gender"),
            photo_url=p2_photo,
            color_id=p2_color,
            is_serving=is_p2_serving,
        )

        def parse_score_val(val: Any) -> Union[int, str]:
            if val is None:
                return 0
            s_val = str(val).strip()
            if s_val.isdigit():
                return int(s_val)
            return s_val if s_val else 0

        # Sets score
        src_score = live_match or m
        p1_sets = parse_score_val(src_score.get("player1Score"))
        p2_sets = parse_score_val(src_score.get("player2Score"))

        score_sets = ScoreSets(
            player1=p1_sets,
            player2=p2_sets,
            formatted=f"{p1_sets}:{p2_sets}",
        )

        # Determine walkover / retired status (e.g. W:L or L:W)
        is_walkover_or_retired = (
            str(p1_sets).strip().upper() in ("W", "L")
            or str(p2_sets).strip().upper() in ("W", "L")
            or m.get("technicalResult") == 1
        )

        # Extract winner_id
        winner_raw = m.get("winner")
        winner_id = None
        if isinstance(winner_raw, dict):
            winner_id = winner_raw.get("id")
        elif isinstance(winner_raw, int):
            winner_id = winner_raw

        # Status mapping:
        # statusId: 1 = upcoming, 2 = live, 3 = finished
        raw_status = m.get("statusId")
        if is_walkover_or_retired:
            status = "finished"
        elif live_match:
            status = "live"
        elif raw_status == 2:
            status = "live"
        elif raw_status == 3 or winner_id is not None:
            status = "finished"
        elif raw_status == 1:
            status = "upcoming"
        else:
            status = "upcoming"

        # Individual set points
        raw_sets = src_score.get("setScores") or m.get("setScores") or []
        score_points: List[SetScore] = []
        for idx, s in enumerate(raw_sets):
            p1_pt = parse_score_val(s.get("p1Score"))
            p2_pt = parse_score_val(s.get("p2Score"))
            set_num = int(s.get("number") or (idx + 1))
            is_current = bool(status == "live" and idx == len(raw_sets) - 1)
            score_points.append(
                SetScore(set=set_num, p1=p1_pt, p2=p2_pt, is_current=is_current)
            )

        time_str, start_iso = self._format_time(m.get("startDate"))

        return MatchItem(
            id=match_id,
            tournament_id=tournament_id,
            tournament_name=tournament_name,
            time=time_str,
            start_date=start_iso,
            stage=stage,
            position=position,
            hall=hall,
            period=period,
            player1=player1,
            player2=player2,
            score_sets=score_sets,
            score_points=score_points,
            status=status,
            raw_status_id=raw_status,
            winner_id=winner_id,
            is_retired=is_walkover_or_retired,
            technical_result=m.get("technicalResult"),
        )

    async def fetch_live_widgets(self) -> Dict[int, Dict[str, Any]]:
        """Fetch real-time live games from widget endpoint."""
        client = await self.get_client()
        try:
            async with self.semaphore:
                resp = await client.get("/api/Matches/widget/ru")
                if resp.status_code == 200:
                    data = resp.json()
                    widgets_by_id = {}
                    for item in data:
                        mid = item.get("id")
                        if mid:
                            widgets_by_id[int(mid)] = item
                    return widgets_by_id
        except Exception as e:
            logger.warning("Failed to fetch /api/Matches/widget/ru: %s", e)
        return {}

    async def fetch_tournaments_by_period(
        self, date: str, period: int
    ) -> List[Dict[str, Any]]:
        """Fetch tournaments for a specific period under rate limiting."""
        client = await self.get_client()
        try:
            async with self.semaphore:
                resp = await client.get(
                    f"/api/Tournaments/ru?date={date}&dayPeriod={period}"
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(
                "Failed to fetch tournaments for date=%s, period=%d: %s", date, period, e
            )
        return []

    async def scrape_schedule_matrix(
        self,
        date: str,
        halls: Optional[List[int]] = None,
        periods: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """Scrapes combinations using the worker pool with Semaphore(10)."""
        await self.load_metadata()
        periods_to_fetch = periods if (periods and len(periods) > 0) else list(range(1, 8))

        # Parallel fetch across periods using semaphore
        tasks = [self.fetch_tournaments_by_period(date, p) for p in periods_to_fetch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        combined_tournaments = []
        for r in results:
            if isinstance(r, list):
                combined_tournaments.extend(r)

        return combined_tournaments

    async def fetch_html_fallback(
        self, date: str, hall: int, period: int
    ) -> List[Dict[str, Any]]:
        """
        HTML scraper fallback targeting:
        https://tabletennis.setkacup.com/ru/schedule?date={date}&hall={hall}&period={period}
        """
        client = await self.get_client()
        url = f"/ru/schedule?date={date}&hall={hall}&period={period}"
        try:
            async with self.semaphore:
                resp = await client.get(url)
                if resp.status_code == 200 and "application-root" not in resp.text:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # In case Setka Cup returns server-rendered HTML table/matches
                    match_cards = soup.select(".match, .match-card, tr.match-row")
                    parsed = []
                    for card in match_cards:
                        # Extract any text contents
                        time_el = card.select_one(".time, .date")
                        p1_el = card.select_one(".player1, .player:first-child")
                        p2_el = card.select_one(".player2, .player:last-child")
                        score_el = card.select_one(".score, .set-scores")
                        parsed.append(
                            {
                                "id": hash(card.text),
                                "time": time_el.text.strip() if time_el else "",
                                "p1": p1_el.text.strip() if p1_el else "",
                                "p2": p2_el.text.strip() if p2_el else "",
                                "score": score_el.text.strip() if score_el else "",
                                "hall": hall,
                                "period": period,
                            }
                        )
                    return parsed
        except Exception as e:
            logger.debug("HTML fallback scrape failed for %s: %s", url, e)
        return []

    async def get_matches(
        self,
        date: Optional[str] = None,
        halls: Optional[List[int]] = None,
        periods: Optional[List[int]] = None,
        status_filter: Optional[str] = None,
        force_refresh: bool = False,
    ) -> MatchesResponse:
        """Primary method to get parsed matches with caching and concurrency control."""
        if not date:
            date = datetime.date.today().strftime("%Y-%m-%d")

        await self.load_metadata()

        cache_key = f"{date}"
        cached_entry = self._cache.get(cache_key)

        all_matches: List[MatchItem] = []
        is_cached = False
        cache_age = 0.0

        if not force_refresh and cached_entry and cached_entry.is_valid(self.cache_ttl):
            all_matches = cached_entry.data
            is_cached = True
            cache_age = round(datetime.datetime.now().timestamp() - cached_entry.timestamp, 1)
        else:
            # Fresh scrape:
            client = await self.get_client()

            # Concurrently fetch day's full tournament feed and active live widgets
            async with self.semaphore:
                tournaments_req = client.get(f"/api/Tournaments/ru?date={date}")
                live_widget_req = client.get("/api/Matches/widget/ru")

                results = await asyncio.gather(
                    tournaments_req, live_widget_req, return_exceptions=True
                )

            tournaments_data: List[Dict[str, Any]] = []
            live_widgets_map: Dict[int, Dict[str, Any]] = {}

            # Process tournaments response
            if not isinstance(results[0], Exception) and results[0].status_code == 200:
                tournaments_data = results[0].json()
            else:
                logger.info(
                    "Single-shot tournament fetch returned error, falling back to period matrix scrape..."
                )
                tournaments_data = await self.scrape_schedule_matrix(date, halls, periods)

            # Process live widgets response
            if not isinstance(results[1], Exception) and results[1].status_code == 200:
                for lw in results[1].json():
                    mid = lw.get("id")
                    if mid:
                        live_widgets_map[int(mid)] = lw

            # Parse and normalize matches
            seen_match_ids = set()
            parsed_matches: List[MatchItem] = []

            for t in tournaments_data:
                t_location_id = t.get("locationId")
                t_period_id = t.get("dayPeriodToken")
                for m in t.get("matches", []):
                    mid = m.get("id")
                    if mid and mid not in seen_match_ids:
                        seen_match_ids.add(mid)
                        item = self._parse_match_obj(
                            m,
                            live_widgets_map=live_widgets_map,
                            default_location_id=t_location_id,
                            default_period_id=t_period_id,
                        )
                        parsed_matches.append(item)

            # Also check if there are live matches in widget that were not yet in tournaments list
            for mid, lw in live_widgets_map.items():
                if mid not in seen_match_ids:
                    seen_match_ids.add(mid)
                    item = self._parse_match_obj(
                        lw,
                        live_widgets_map=live_widgets_map,
                    )
                    parsed_matches.append(item)

            # Sort matches: live first, then upcoming by start time, then finished
            def sort_key(item: MatchItem):
                status_priority = {"live": 0, "upcoming": 1, "finished": 2}
                priority = status_priority.get(item.status, 3)
                start_date = item.start_date or ""
                return (priority, start_date, item.position or 0)

            parsed_matches.sort(key=sort_key)

            # Update cache
            self._cache[cache_key] = CacheEntry(
                data=parsed_matches, timestamp=datetime.datetime.now().timestamp()
            )
            all_matches = parsed_matches

        # Calculate counts
        counts = {
            "all": len(all_matches),
            "live": sum(1 for m in all_matches if m.status == "live"),
            "upcoming": sum(1 for m in all_matches if m.status == "upcoming"),
            "finished": sum(1 for m in all_matches if m.status == "finished"),
        }

        # Apply filtering
        filtered = all_matches

        if halls:
            halls_set = set(halls)
            filtered = [m for m in filtered if m.hall.id in halls_set]

        if periods:
            periods_set = set(periods)
            filtered = [m for m in filtered if m.period.id in periods_set]

        if status_filter and status_filter.lower() != "all":
            sf = status_filter.lower()
            filtered = [m for m in filtered if m.status.lower() == sf]

        return MatchesResponse(
            total=len(filtered),
            counts=counts,
            date=date,
            halls_filter=halls,
            periods_filter=periods,
            status_filter=status_filter or "all",
            cached=is_cached,
            cache_age_seconds=cache_age if is_cached else 0.0,
            matches=filtered,
        )

    async def get_all_halls(self) -> List[HallInfo]:
        await self.load_metadata()
        return sorted(self._halls_map.values(), key=lambda h: h.id)

    async def get_all_periods(self) -> List[PeriodInfo]:
        await self.load_metadata()
        periods = list(self._periods_map.values())
        if not periods:
            periods = [
                PeriodInfo(id=k, name=v) for k, v in DEFAULT_PERIOD_NAMES.items()
            ]
        return sorted(periods, key=lambda p: p.id)
