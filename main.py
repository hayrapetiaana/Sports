import os
import sys
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from models import (
    HallInfo,
    MatchesResponse,
    PeriodInfo,
    TTCupTournament,
    TTCupScheduleDetail,
    TTCupMatchesResponse,
    TTCupConfigUpdate,
    LeagueProTournament,
    LeagueProMatch,
    LeagueProMatchesResponse,
    SportLigaTournament,
    SportLigaMatch,
    SportLigaMatchesResponse,
    UnifiedMatchItem,
    UnifiedMatchesResponse,
    RemovedMatchItem,
    RemovedMatchesResponse,
    EsportsMatchItem,
    EsportsResponse,
    EsportsRemovedMatchItem,
    EsportsRemovedMatchesResponse,
    HLTVConfigUpdate,
    LiquipediaConfigUpdate,
)
from scraper import SetkaCupScraper
from ttcup_scraper import TTCupScraper
from league_pro_scraper import LeagueProScraper
from sport_liga_scraper import SportLigaScraper
from liquipedia_scraper import liquipedia_scraper, DISCIPLINES
from hltv_scraper import hltv_scraper, parse_hltv_cookie_input

TTCUP_COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ttcup_cookie.txt")

# Initialize scrapers with 30s cache TTL and concurrency limits
scraper = SetkaCupScraper(cache_ttl=30.0, max_concurrency=10)
ttcup_scraper = TTCupScraper(cache_ttl=30.0, max_concurrency=8)
league_pro_scraper = LeagueProScraper(cache_ttl=30.0, max_concurrency=8)
sport_liga_scraper = SportLigaScraper(cache_ttl=30.0, max_concurrency=8)

if os.path.exists(TTCUP_COOKIE_FILE):
    try:
        with open(TTCUP_COOKIE_FILE, "r", encoding="utf-8") as _f:
            _saved_init_cookie = _f.read().strip()
            if _saved_init_cookie:
                ttcup_scraper.set_config(cookie=_saved_init_cookie)
    except Exception as _e:
        print(f"Warning pre-loading TT Cup cookie: {_e}")


class MatchCacheManager:
    """
    Maintains a resilient match cache across all scraping platforms.
    - If a match was scraped in one refresh and vanishes in the next, it stays in cache
      if it is logically valid (valid player names, valid time).
    - If a match receives no update for 5 minutes (300 seconds), it is retired from active
      matches and recorded in removed_matches with removal timestamp and reason.
    - Tracks and serves removed matches through the /api/removed-matches API.
    """
    def __init__(self, grace_period_sec: float = 300.0):
        self.grace_period_sec = grace_period_sec
        # key: str (match.id) -> Dict
        self._cache: dict = {}
        # key: str -> Dict of removed match
        self._removed_history: dict = {}

    def process_matches(
        self,
        newly_scraped: List[UnifiedMatchItem],
        platform_filter: str,
        date_from: str,
        date_to: str,
    ) -> List[UnifiedMatchItem]:
        import datetime
        now = datetime.datetime.now().timestamp()
        seen_keys = set()

        for m in newly_scraped:
            key = m.id
            seen_keys.add(key)
            if key in self._cache:
                entry = self._cache[key]
                entry["match"] = m
                entry["last_seen_at"] = now
                if entry.get("is_removed"):
                    entry["is_removed"] = False
                    entry["removed_at"] = None
                    entry["removed_reason"] = None
            else:
                self._cache[key] = {
                    "match": m,
                    "platform": m.platform,
                    "date": (m.start_date.split("T")[0] if m.start_date else None) or date_from,
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "is_removed": False,
                    "removed_at": None,
                    "removed_reason": None,
                }

        # Build active matches starting with newly scraped
        active_matches_map = {m.id: m for m in newly_scraped}

        # Check existing cached matches that were NOT returned in this scrape
        for key, entry in list(self._cache.items()):
            if key in seen_keys or entry.get("is_removed"):
                continue

            m = entry["match"]
            # Platform check: only check for the platforms that were actively requested
            if platform_filter != "all":
                req_plats = [platform_filter]
                if platform_filter in ("sport_liga", "sportliga", "liga_pro", "ligapro"):
                    req_plats = ["sport_liga", "liga_pro"]
                elif platform_filter in ("league_pro", "leaguepro"):
                    req_plats = ["league_pro"]
                if m.platform not in req_plats:
                    continue

            # Date check
            m_date = entry.get("date") or date_from
            if not (date_from <= m_date <= date_to):
                continue

            time_since_seen = now - entry["last_seen_at"]
            # Validate if match is logically okay
            p1 = (m.player1_name or "").strip()
            p2 = (m.player2_name or "").strip()
            is_valid = bool(p1 and p2 and p1 != "-" and p2 != "-")

            if is_valid and time_since_seen < self.grace_period_sec:
                # Within 5 minutes: keep it in active matches!
                active_matches_map[key] = m
            elif time_since_seen >= self.grace_period_sec:
                # 5 minutes elapsed without an update: retire match!
                entry["is_removed"] = True
                entry["removed_at"] = now
                entry["removed_reason"] = "Не поступало обновлений более 5 минут (исчез из скрапера)"
                self._removed_history[key] = entry

        return list(active_matches_map.values())

    def record_removed(self, match: UnifiedMatchItem, reason: str):
        import datetime
        now = datetime.datetime.now().timestamp()
        key = match.id
        entry = {
            "match": match,
            "platform": match.platform,
            "date": (match.start_date.split("T")[0] if match.start_date else None) or "today",
            "first_seen_at": now - 60,
            "last_seen_at": now - 30,
            "is_removed": True,
            "removed_at": now,
            "removed_reason": reason,
        }
        self._cache[key] = entry
        self._removed_history[key] = entry

    def get_removed_matches(self, platform: Optional[str] = None) -> List[RemovedMatchItem]:
        items: List[RemovedMatchItem] = []
        for key, entry in self._removed_history.items():
            m = entry["match"]
            if platform and platform != "all" and m.platform != platform:
                continue
            items.append(
                RemovedMatchItem(
                    id=m.id,
                    platform=m.platform,
                    platform_name=m.platform_name,
                    tournament_name=m.tournament_name,
                    stage=m.stage,
                    start_date=m.start_date,
                    time=m.time,
                    country=m.country,
                    country_code=m.country_code,
                    player1_name=m.player1_name,
                    player1_photo=m.player1_photo,
                    player2_name=m.player2_name,
                    player2_photo=m.player2_photo,
                    score=m.score,
                    set_scores=m.set_scores,
                    status=m.status,
                    url=m.url,
                    first_seen_at=entry.get("first_seen_at", 0),
                    last_seen_at=entry.get("last_seen_at", 0),
                    removed_at=entry.get("removed_at", 0),
                    removed_reason=entry.get("removed_reason", "Удален скрапером"),
                )
            )
        items.sort(key=lambda x: x.removed_at, reverse=True)
        return items

    def clear_removed(self):
        self._removed_history.clear()

    def restore_match(self, match_id: str) -> bool:
        import datetime
        now = datetime.datetime.now().timestamp()
        if match_id in self._removed_history:
            entry = self._removed_history.pop(match_id)
            entry["is_removed"] = False
            entry["last_seen_at"] = now
            entry["removed_at"] = None
            entry["removed_reason"] = None
            self._cache[match_id] = entry
            return True
        return False


match_cache_manager = MatchCacheManager(grace_period_sec=300.0)


class EsportsCacheManager:
    """
    Maintains a resilient match cache for esports across Liquipedia and HLTV.
    - If a match was scraped in one refresh and vanishes in the next, it stays in cache
      for up to 5 minutes (300 seconds) if it is logically sound.
    - If a match receives no update for 5 minutes, it is retired to removed_matches.
    """
    def __init__(self, grace_period_sec: float = 300.0):
        self.grace_period_sec = grace_period_sec
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._removed_history: Dict[str, Dict[str, Any]] = {}

    def process_matches(
        self, newly_scraped: List[EsportsMatchItem], discipline_filter: str = "all"
    ) -> List[EsportsMatchItem]:
        import datetime
        now = datetime.datetime.now().timestamp()
        seen_keys = set()

        for m in newly_scraped:
            key = m.id
            seen_keys.add(key)
            if key in self._cache:
                entry = self._cache[key]
                entry["match"] = m
                entry["last_seen_at"] = now
                if entry.get("is_removed"):
                    entry["is_removed"] = False
                    entry["removed_at"] = None
                    entry["removed_reason"] = None
            else:
                self._cache[key] = {
                    "match": m,
                    "discipline": m.discipline,
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "is_removed": False,
                    "removed_at": None,
                    "removed_reason": None,
                }

        active_matches_map = {m.id: m for m in newly_scraped}

        for key, entry in list(self._cache.items()):
            if key in seen_keys or entry.get("is_removed"):
                continue

            m = entry["match"]
            if discipline_filter != "all" and m.discipline != discipline_filter:
                continue

            time_since_seen = now - entry["last_seen_at"]
            is_valid = bool(m.team1_name and m.team2_name and m.team1_name != "TBD")

            if is_valid and time_since_seen < self.grace_period_sec:
                active_matches_map[key] = m
            elif time_since_seen >= self.grace_period_sec:
                entry["is_removed"] = True
                entry["removed_at"] = now
                entry["removed_reason"] = "Не поступало обновлений более 5 минут (исчез из скрапера)"
                self._removed_history[key] = entry

        return list(active_matches_map.values())

    def get_removed_matches(self, discipline: Optional[str] = None) -> List[EsportsRemovedMatchItem]:
        items: List[EsportsRemovedMatchItem] = []
        for key, entry in self._removed_history.items():
            m = entry["match"]
            if discipline and discipline != "all" and m.discipline != discipline:
                continue
            items.append(
                EsportsRemovedMatchItem(
                    id=m.id,
                    discipline=m.discipline,
                    discipline_name=m.discipline_name,
                    tournament_name=m.tournament_name,
                    stage=m.stage,
                    format=m.format,
                    team1_name=m.team1_name,
                    team1_short=m.team1_short,
                    team2_name=m.team2_name,
                    team2_short=m.team2_short,
                    score=m.score,
                    status=m.status,
                    start_date=m.start_date,
                    time=m.time,
                    stream_url=m.stream_url,
                    stream_platform=m.stream_platform,
                    source=m.source,
                    source_url=m.source_url,
                    first_seen_at=entry.get("first_seen_at", 0),
                    last_seen_at=entry.get("last_seen_at", 0),
                    removed_at=entry.get("removed_at", 0),
                    removed_reason=entry.get("removed_reason", "Удален скрапером"),
                )
            )
        items.sort(key=lambda x: x.removed_at, reverse=True)
        return items

    def clear_removed(self):
        self._removed_history.clear()

    def restore_match(self, match_id: str) -> bool:
        import datetime
        now = datetime.datetime.now().timestamp()
        if match_id in self._removed_history:
            entry = self._removed_history.pop(match_id)
            entry["is_removed"] = False
            entry["last_seen_at"] = now
            entry["removed_at"] = None
            entry["removed_reason"] = None
            self._cache[match_id] = entry
            return True
        return False


esports_cache_manager = EsportsCacheManager(grace_period_sec=300.0)



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: preload metadata in background and load saved TT Cup cookie
    try:
        await scraper.load_metadata()
    except Exception as e:
        print(f"Warning during startup metadata preload: {e}")

    if os.path.exists(TTCUP_COOKIE_FILE):
        try:
            with open(TTCUP_COOKIE_FILE, "r", encoding="utf-8") as f:
                saved_cookie = f.read().strip()
                if saved_cookie:
                    ttcup_scraper.set_config(cookie=saved_cookie)
                    print(f"Loaded persistent TT Cup cookie ({len(saved_cookie)} chars)")
        except Exception as e:
            print(f"Warning loading saved TT Cup cookie: {e}")

    yield
    # Shutdown: cleanly close HTTP connections
    await scraper.close()
    await ttcup_scraper.close()
    await league_pro_scraper.close()
    await sport_liga_scraper.close()



app = FastAPI(
    title="Setka Cup Real-Time Match Monitor",
    description="Real-time table tennis monitoring API and dashboard for Setka Cup",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow CORS for local dev / remote frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directory exists
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def parse_int_list(val: Optional[str]) -> Optional[List[int]]:
    if not val or val.strip().lower() in ("all", "*", ""):
        return None
    res = []
    for item in val.split(","):
        item = item.strip()
        if item.isdigit():
            res.append(int(item))
    return res if res else None


@app.get("/api/matches", response_model=MatchesResponse)
async def get_matches(
    date: Optional[str] = Query(
        None,
        description="Match date in format YYYY-MM-DD. Defaults to today.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    hall: Optional[str] = Query(
        None,
        description="Hall ID or comma-separated hall IDs (e.g. '2,3,15' or 'all')",
    ),
    period: Optional[str] = Query(
        None,
        description="Period ID (1-7) or comma-separated period IDs (e.g. '1,2' or 'all')",
    ),
    status: Optional[str] = Query(
        "all",
        description="Filter status: 'all', 'live', 'upcoming', 'finished'",
    ),
    from_time: Optional[str] = Query(
        None,
        description="Start time filter e.g. '10:00' or ISO datetime",
    ),
    to_time: Optional[str] = Query(
        None,
        description="End time filter e.g. '18:00' or ISO datetime",
    ),
    search: Optional[str] = Query(
        None,
        description="Filter by player name or hall name",
    ),
    force_refresh: bool = Query(
        False,
        description="Bypass server-side cache and force fresh scrape",
    ),
):
    """
    Fetch and return parsed table tennis matches from Setka Cup.
    Supports concurrency limits, server-side caching (TTL ~30s),
    hall/period parameter filtering, timeframe range, and live search.
    """
    try:
        halls_list = parse_int_list(hall)
        periods_list = parse_int_list(period)

        response = await scraper.get_matches(
            date=date,
            halls=halls_list,
            periods=periods_list,
            status_filter=status,
            force_refresh=force_refresh,
        )

        filtered_matches = response.matches

        # Apply timeframe filter if provided (e.g. "12:00" - "16:00")
        if from_time or to_time:
            def match_in_timeframe(m):
                # Use m.time (HH:MM) or start_date
                time_str = m.time or ""
                if from_time and time_str < from_time:
                    return False
                if to_time and time_str > to_time:
                    return False
                return True

            filtered_matches = [m for m in filtered_matches if match_in_timeframe(m)]

        # Apply search filter if provided
        if search and search.strip():
            query = search.strip().lower()
            filtered_matches = [
                m
                for m in filtered_matches
                if query in m.player1.name.lower()
                or query in m.player2.name.lower()
                or query in m.hall.name.lower()
                or query in m.stage.lower()
            ]

        response.matches = filtered_matches
        response.total = len(filtered_matches)

        return response
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to scrape match data: {str(e)}"
        )


@app.get("/api/player-photo/{photo_token}")
async def get_player_photo(photo_token: str):
    """
    Proxy and cache player photos to bypass third-party hotlink / CORS blocking.
    """
    from fastapi.responses import Response

    if not photo_token or photo_token.strip() in ("", "-"):
        raise HTTPException(status_code=404, detail="No photo token provided")

    photo_bytes = await scraper.fetch_player_photo(photo_token.strip())
    if not photo_bytes:
        raise HTTPException(status_code=404, detail="Player photo not found")

    return Response(
        content=photo_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/api/halls", response_model=List[HallInfo])
async def get_halls():
    """Returns all available halls/locations with their IDs and stream URLs."""
    try:
        return await scraper.get_all_halls()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/periods", response_model=List[PeriodInfo])
async def get_periods():
    """Returns day periods (1 to 7) with their Russian/English names."""
    try:
        return await scraper.get_all_periods()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# TT Cup (ttcup.com) API Endpoints
# ==============================================================================

@app.get("/api/ttcup/tournaments", response_model=List[TTCupTournament])
async def get_ttcup_tournaments(
    date: Optional[str] = Query(
        None,
        description="Date in format YYYY-MM-DD or DD.MM.YYYY. Defaults to today.",
    ),
    country: Optional[str] = Query(
        None,
        description="Filter by country: 'czech', 'poland', or 'all'",
    ),
    force_refresh: bool = Query(
        False,
        description="Bypass cache and force re-scrape",
    ),
):
    """
    List available tournaments on ttcup.com for a specific day.
    Identifies whether each tournament is from the Czech Republic or Poland,
    its hall ID, start time, and schedule URL.
    """
    try:
        tournaments, _ = await ttcup_scraper.get_tournaments(
            date=date, country=country, force_refresh=force_refresh
        )
        return tournaments
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch TT Cup tournaments: {str(e)}"
        )


@app.get("/api/ttcup/schedule", response_model=TTCupScheduleDetail)
async def get_ttcup_schedule(
    hall: int = Query(
        ...,
        description="Hall ID to fetch schedule for (e.g. 3, 22, 9)",
    ),
    date: Optional[str] = Query(
        None,
        description="Date in format YYYY-MM-DD or DD.MM.YYYY. Defaults to today.",
    ),
    force_refresh: bool = Query(
        False,
        description="Bypass cache and force re-scrape",
    ),
):
    """
    Fetch the detailed schedule and standings for a specific tournament hall
    (e.g. https://ttcup.com/schedule/17.09.2026/h:3/ or /h:22/).
    """
    try:
        return await ttcup_scraper.get_tournament_schedule(
            date=date, hall_id=hall, force_refresh=force_refresh
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch TT Cup schedule for hall {hall}: {str(e)}",
        )


@app.get("/api/ttcup/matches", response_model=TTCupMatchesResponse)
async def get_ttcup_matches(
    date: Optional[str] = Query(
        None,
        description="Date in format YYYY-MM-DD or DD.MM.YYYY. Defaults to today.",
    ),
    country: Optional[str] = Query(
        None,
        description="Filter by country: 'czech', 'poland', or 'all'",
    ),
    hall: Optional[str] = Query(
        None,
        description="Filter by hall ID or comma-separated list of hall IDs (e.g. '3,22')",
    ),
    from_time: Optional[str] = Query(
        None,
        description="Earliest match time e.g. '10:00'",
    ),
    to_time: Optional[str] = Query(
        None,
        description="Latest match time e.g. '18:00'",
    ),
    status: Optional[str] = Query(
        "all",
        description="Filter status: 'all', 'live', 'upcoming', 'finished'",
    ),
    search: Optional[str] = Query(
        None,
        description="Filter by player name, tournament name, or stage",
    ),
    force_refresh: bool = Query(
        False,
        description="Bypass cache and force re-scrape",
    ),
):
    """
    Fetch and aggregate matches from ttcup.com for Czech Republic and Poland tournaments.
    Supports filtering by selected date, country, tournament/hall, time frame window
    (from_time to to_time), match status, and player name search.
    """
    try:
        halls_list = parse_int_list(hall)
        return await ttcup_scraper.get_matches(
            date=date,
            country=country,
            halls=halls_list,
            from_time=from_time,
            to_time=to_time,
            status_filter=status,
            search=search,
            force_refresh=force_refresh,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to scrape TT Cup matches: {str(e)}"
        )


@app.get("/api/ttcup/config")
async def get_ttcup_config():
    """
    Returns current TT Cup cookie configuration and scraping health status.
    """
    has_cookie = bool(ttcup_scraper._custom_cookie)
    snippet = None
    if has_cookie and ttcup_scraper._custom_cookie:
        c = ttcup_scraper._custom_cookie
        snippet = (c[:25] + "..." + c[-15:]) if len(c) > 42 else c
    return {
        "status": "success",
        "cookie_set": has_cookie,
        "cookie_snippet": snippet,
        "cookies_count": len(ttcup_scraper._custom_cookies_dict),
        "cookie_names": list(ttcup_scraper._custom_cookies_dict.keys()),
        "proxy_set": bool(ttcup_scraper._custom_proxy),
        "captcha_required": ttcup_scraper.captcha_detected,
    }


@app.post("/api/ttcup/config")
async def update_ttcup_config(config: TTCupConfigUpdate):
    """
    Update session cookies (string, JSON array, or dict) or proxy for TTCup scraping and persist to file.
    Useful when running in environments where anti-bot verification was completed.
    """
    import json
    cookie = config.cookie
    ttcup_scraper.set_config(cookie=cookie, proxy=config.proxy)
    try:
        with open(TTCUP_COOKIE_FILE, "w", encoding="utf-8") as f:
            if isinstance(cookie, (dict, list)):
                f.write(json.dumps(cookie, indent=4, ensure_ascii=False))
            elif isinstance(cookie, str):
                f.write(cookie.strip())
            else:
                f.write("")
    except Exception as e:
        print(f"Error persisting TT Cup cookie to file: {e}")

    return {
        "status": "success",
        "cookie_set": bool(ttcup_scraper._custom_cookie),
        "cookies_count": len(ttcup_scraper._custom_cookies_dict),
        "cookie_names": list(ttcup_scraper._custom_cookies_dict.keys()),
        "proxy_set": bool(ttcup_scraper._custom_proxy),
        "captcha_required": ttcup_scraper.captcha_detected,
    }


@app.get("/api/ttcup/status")
async def get_ttcup_status():
    """Returns TT Cup scraper health and challenge status."""
    return {
        "status": "online",
        "captcha_required": ttcup_scraper.captcha_detected,
        "has_custom_cookie": bool(ttcup_scraper._custom_cookie),
        "cached_tournaments": list(ttcup_scraper._tournaments_cache.keys()),
        "cached_schedules": list(ttcup_scraper._schedule_cache.keys()),
    }


# ==============================================================================
# Removed Matches Endpoints
# ==============================================================================

@app.get("/api/removed-matches", response_model=RemovedMatchesResponse)
async def get_removed_matches(
    platform: Optional[str] = Query(None, description="Filter removed matches by platform"),
):
    """
    Returns list of matches that were removed (e.g. absent from scraper for > 5 minutes, or cancelled).
    """
    items = match_cache_manager.get_removed_matches(platform=platform)
    return RemovedMatchesResponse(total=len(items), matches=items)


@app.post("/api/removed-matches/clear")
async def clear_removed_matches():
    """Clear removed matches history."""
    match_cache_manager.clear_removed()
    return {"status": "success", "message": "Removed matches history cleared"}


@app.post("/api/removed-matches/restore/{match_id}")
async def restore_removed_match(match_id: str):
    """Restore a previously removed match back to active matches."""
    restored = match_cache_manager.restore_match(match_id)
    if not restored:
        raise HTTPException(status_code=404, detail="Match not found in removed history")
    return {"status": "success", "message": f"Match {match_id} restored"}


# ==============================================================================
# League Pro (tt.league-pro.com) Endpoints
# ==============================================================================

@app.get("/api/leaguepro/tournaments", response_model=List[LeagueProTournament])
async def get_leaguepro_tournaments(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    import datetime
    today = datetime.date.today().isoformat()
    d_from = date_from or today
    d_to = date_to or today
    return await league_pro_scraper.get_tournaments(d_from, d_to)


@app.get("/api/leaguepro/matches", response_model=LeagueProMatchesResponse)
async def get_leaguepro_matches(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    tournament_id: Optional[int] = Query(None, description="Tournament ID filter"),
    status: Optional[str] = Query("all", description="Status: 'all', 'live', 'upcoming', 'finished'"),
    from_time: Optional[str] = Query(None, description="Filter matches starting after HH:MM"),
    to_time: Optional[str] = Query(None, description="Filter matches starting before HH:MM"),
    search: Optional[str] = Query(None, description="Search player or tournament"),
):
    import datetime
    today = datetime.date.today().isoformat()
    d_from = date_from or today
    d_to = date_to or today
    return await league_pro_scraper.get_matches(
        date_from=d_from,
        date_to=d_to,
        tournament_filter=tournament_id,
        status_filter=status,
        from_time=from_time,
        to_time=to_time,
        search=search,
    )


# ==============================================================================
# Sport-Liga Pro (sport-liga.pro) Endpoints
# ==============================================================================

@app.get("/api/sportliga/tournaments", response_model=List[SportLigaTournament])
@app.get("/api/ligapro/tournaments", response_model=List[SportLigaTournament])
async def get_sportliga_tournaments(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    date: Optional[str] = Query(None, description="Single date YYYY-MM-DD fallback"),
):
    import datetime
    today = datetime.date.today().isoformat()
    d_from = date or date_from or today
    d_to = date or date_to or today
    return await sport_liga_scraper.get_tournaments(d_from, d_to)


@app.get("/api/sportliga/matches", response_model=SportLigaMatchesResponse)
@app.get("/api/ligapro/matches", response_model=SportLigaMatchesResponse)
async def get_sportliga_matches(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    date: Optional[str] = Query(None, description="Single date YYYY-MM-DD fallback"),
    tournament_id: Optional[int] = Query(None, description="Tournament ID filter"),
    status: Optional[str] = Query("all", description="Status: 'all', 'live', 'upcoming', 'finished'"),
    from_time: Optional[str] = Query(None, description="Filter matches starting after HH:MM"),
    to_time: Optional[str] = Query(None, description="Filter matches starting before HH:MM"),
    search: Optional[str] = Query(None, description="Search player or tournament"),
):
    import datetime
    today = datetime.date.today().isoformat()
    d_from = date or date_from or today
    d_to = date or date_to or today
    return await sport_liga_scraper.get_matches(
        date_from=d_from,
        date_to=d_to,
        tournament_filter=tournament_id,
        status_filter=status,
        from_time=from_time,
        to_time=to_time,
        search=search,
    )


# ==============================================================================
# Unified 4-Resource Aggregator Endpoint
# ==============================================================================

@app.get("/api/all/matches", response_model=UnifiedMatchesResponse)
async def get_all_unified_matches(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    platform: Optional[str] = Query("all", description="Filter platform: 'all', 'setka', 'ttcup', 'league_pro', 'sport_liga', 'liga_pro'"),
    status: Optional[str] = Query("all", description="Filter status: 'all', 'live', 'upcoming', 'finished'"),
    from_time: Optional[str] = Query(None, description="Filter matches starting after HH:MM"),
    to_time: Optional[str] = Query(None, description="Filter matches starting before HH:MM"),
    search: Optional[str] = Query(None, description="Search player or tournament"),
):
    import datetime
    import asyncio
    today = datetime.date.today().isoformat()
    d_from = date_from or today
    d_to = date_to or today

    unified_matches: List[UnifiedMatchItem] = []
    platform_counts = {"setka": 0, "ttcup": 0, "league_pro": 0, "sport_liga": 0, "liga_pro": 0}

    # Prepare async tasks
    async def fetch_setka():
        # Setka Cup takes a single date, query d_from
        try:
            res = await scraper.get_matches(
                date=d_from,
                status_filter=status if status != "all" else None,
            )
            items = []
            for m in res.matches:
                items.append(
                    UnifiedMatchItem(
                        id=f"setka_{m.id}",
                        platform="setka",
                        platform_name="Setka Cup",
                        tournament_name=m.tournament_name or m.stage,
                        stage=m.stage,
                        start_date=m.start_date,
                        time=m.time,
                        country="Ukraine",
                        country_code="ua",
                        player1_name=m.player1.name,
                        player1_photo=m.player1.photo_url,
                        player2_name=m.player2.name,
                        player2_photo=m.player2.photo_url,
                        score=m.score_sets.formatted if m.score_sets else "-",
                        set_scores=", ".join(f"{p.p1}:{p.p2}" for p in m.score_points) if m.score_points else None,
                        status=m.status,
                        url=m.hall.stream_url if m.hall else None,
                    )
                )
            return ("setka", items)
        except Exception as e:
            print(f"Error fetching Setka for unified view: {e}")
            return ("setka", [])

    async def fetch_ttcup():
        try:
            res = await ttcup_scraper.get_matches(
                date=d_from,
                status_filter=status or "all",
                from_time=from_time,
                to_time=to_time,
                search=search,
            )
            dedup_items: Dict[str, UnifiedMatchItem] = {}
            for m in res.matches:
                p1 = (m.player1_name or "").strip().lower()
                p2 = (m.player2_name or "").strip().lower()
                pair_key = "_vs_".join(sorted([p1, p2]))
                time_key = (m.time or "")[:5]
                date_key = (m.start_date or "").split("T")[0] or d_from
                dedup_key = f"{date_key}_{time_key}_{pair_key}"

                c_code = "pl" if m.country == "Poland" else ("cz" if m.country == "Czech Republic" else "unknown")
                item = UnifiedMatchItem(
                    id=f"ttcup_{m.hall_id}_{m.order or m.time}",
                    platform="ttcup",
                    platform_name="TT Cup",
                    tournament_name=m.tournament_name,
                    stage=m.stage,
                    start_date=m.start_date,
                    time=m.time,
                    country=m.country,
                    country_code=c_code,
                    player1_name=m.player1_name,
                    player2_name=m.player2_name,
                    score=m.score,
                    set_scores=m.set_scores,
                    status=m.status,
                    url=m.vs_url,
                )

                if dedup_key not in dedup_items:
                    dedup_items[dedup_key] = item
                else:
                    existing = dedup_items[dedup_key]
                    if item.score not in ("-", "", "0:0") and existing.score in ("-", "", "0:0"):
                        dedup_items[dedup_key] = item
                    elif item.status in ("live", "finished") and existing.status not in ("live", "finished"):
                        dedup_items[dedup_key] = item

            return ("ttcup", list(dedup_items.values()))
        except Exception as e:
            print(f"Error fetching TT Cup for unified view: {e}")
            return ("ttcup", [])

    async def fetch_league_pro():
        try:
            res = await league_pro_scraper.get_matches(
                date_from=d_from,
                date_to=d_to,
                status_filter=status or "all",
                from_time=from_time,
                to_time=to_time,
                search=search,
            )
            items = []
            for m in res.matches:
                items.append(
                    UnifiedMatchItem(
                        id=f"leaguepro_{m.id}",
                        platform="league_pro",
                        platform_name="League Pro",
                        tournament_id=str(m.tournament_id),
                        tournament_name=m.tournament_name,
                        stage=m.stage,
                        start_date=m.start_date,
                        time=m.time,
                        country="Czech Republic",
                        country_code="cz",
                        player1_name=m.player1.name,
                        player1_photo=m.player1.avatar,
                        player2_name=m.player2.name,
                        player2_photo=m.player2.avatar,
                        score=m.score,
                        set_scores=m.set_scores,
                        status=m.status,
                        url=f"https://tt.league-pro.com/en/tournaments/{m.tournament_id}/{m.id}",
                    )
                )
            return ("league_pro", items)
        except Exception as e:
            print(f"Error fetching League Pro for unified view: {e}")
            return ("league_pro", [])

    async def fetch_sport_liga():
        try:
            res = await sport_liga_scraper.get_matches(
                date_from=d_from,
                date_to=d_to,
                status_filter=status or "all",
                from_time=from_time,
                to_time=to_time,
                search=search,
            )
            items = []
            for m in res.matches:
                items.append(
                    UnifiedMatchItem(
                        id=f"ligapro_{m.id}",
                        platform="sport_liga",
                        platform_name="Liga Pro",
                        tournament_id=str(m.tournament_id),
                        tournament_name=m.tournament_name,
                        stage=m.stage,
                        start_date=m.start_date,
                        time=m.time,
                        country=m.country or "Russia",
                        country_code=m.country_code or "ru",
                        city=m.city or "Moscow",
                        player1_name=m.player1.name,
                        player1_photo=m.player1.avatar,
                        player2_name=m.player2.name,
                        player2_photo=m.player2.avatar,
                        score=m.score,
                        set_scores=m.set_scores,
                        status=m.status,
                        url=f"https://www.sport-liga.pro/en/table-tennis?date={d_from}",
                    )
                )
            return ("sport_liga", items)
        except Exception as e:
            print(f"Error fetching Liga Pro for unified view: {e}")
            return ("sport_liga", [])

    # Gather results concurrently
    tasks = []
    selected_platform = (platform or "all").lower().strip()

    if selected_platform in ("all", "setka"):
        tasks.append(fetch_setka())
    if selected_platform in ("all", "ttcup"):
        tasks.append(fetch_ttcup())
    if selected_platform in ("all", "league_pro", "leaguepro"):
        tasks.append(fetch_league_pro())
    if selected_platform in ("all", "sport_liga", "sportliga", "liga_pro", "ligapro"):
        tasks.append(fetch_sport_liga())

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, tuple) and len(r) == 2:
            p_name, items = r
            platform_counts[p_name] = len(items)
            if p_name == "sport_liga":
                platform_counts["liga_pro"] = len(items)
            unified_matches.extend(items)

    # Process through MatchCacheManager with 5-minute retention for disappearing matches
    unified_matches = match_cache_manager.process_matches(
        newly_scraped=unified_matches,
        platform_filter=selected_platform,
        date_from=d_from,
        date_to=d_to,
    )

    # Recalculate platform counts including retained matches
    for p in platform_counts.keys():
        platform_counts[p] = sum(1 for m in unified_matches if m.platform == p or (p == "liga_pro" and m.platform == "sport_liga"))

    # Sort all matches chronologically by start_date / time
    unified_matches.sort(
        key=lambda m: (
            m.start_date or f"{d_from}T{m.time}:00",
            m.time,
        )
    )

    # Helper to test if a finished match ended within last ~10-15 minutes
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    def is_just_finished(m: UnifiedMatchItem) -> bool:
        if m.status != "finished":
            return False
        if m.start_date:
            try:
                st = datetime.datetime.fromisoformat(m.start_date.replace("Z", "+00:00"))
                end_est = st + datetime.timedelta(minutes=18)
                diff_sec = (now_utc - end_est).total_seconds()
                return -300 <= diff_sec <= 720 or 600 <= (now_utc - st).total_seconds() <= 2100
            except Exception:
                pass
        return False

    counts = {
        "all": len(unified_matches),
        "live": sum(1 for m in unified_matches if m.status == "live"),
        "upcoming": sum(1 for m in unified_matches if m.status == "upcoming"),
        "finished": sum(1 for m in unified_matches if m.status == "finished"),
        "just_finished": sum(1 for m in unified_matches if is_just_finished(m)),
    }

    if status and status.lower() == "just_finished":
        unified_matches = [m for m in unified_matches if is_just_finished(m)]

    return UnifiedMatchesResponse(
        total=len(unified_matches),
        counts=counts,
        platform_counts=platform_counts,
        date_from=d_from,
        date_to=d_to,
        from_time=from_time,
        to_time=to_time,
        status_filter=status,
        platform_filter=platform,
        search=search,
        matches=unified_matches,
    )



# ==============================================================================
# Esports Endpoints (Liquipedia + HLTV)
# ==============================================================================

@app.get("/esports", response_class=HTMLResponse)
async def serve_esports():
    """Serve the dedicated Esports multi-discipline dashboard."""
    esports_path = os.path.join(STATIC_DIR, "esports.html")
    if os.path.exists(esports_path):
        return FileResponse(esports_path)
    return HTMLResponse(
        "<h1>Esports Dashboard is loading... Please ensure static/esports.html is created.</h1>"
    )


@app.get("/api/esports/disciplines")
async def get_esports_disciplines():
    """Return all available esports disciplines with metadata and icons."""
    return {
        "disciplines": [
            {
                "id": k,
                "name": v["name"],
                "icon": v["icon"],
                "color": v["color"],
                "twitch_game": v.get("twitch_game"),
            }
            for k, v in DISCIPLINES.items()
        ]
    }


@app.get("/api/esports/matches", response_model=EsportsResponse)
async def get_esports_matches(
    discipline: Optional[str] = Query("all", description="Discipline slug (dota2, counterstrike, valorant...)"),
    status: Optional[str] = Query("all", description="Status filter: all, live, upcoming, finished"),
    date: Optional[str] = Query(None, description="Date filter YYYY-MM-DD"),
    search: Optional[str] = Query(None, description="Search team or tournament name"),
):
    """
    Fetch esports matches from Liquipedia (25+ disciplines) and HLTV (Counter-Strike).
    Enriches CS matches with any missing matches from HLTV.
    Maintains 5-minute resilience cache for disappearing matches.
    """
    disc = (discipline or "all").lower().strip()
    if disc == "cs":
        disc = "counterstrike"

    # 1. Fetch Liquipedia matches
    scraped_matches: List[EsportsMatchItem] = []
    if disc != "all" and disc in DISCIPLINES:
        scraped_matches = await liquipedia_scraper.get_discipline_matches(disc)
    else:
        # All 27 cyber sports disciplines
        scraped_matches = await liquipedia_scraper.get_all_matches(list(DISCIPLINES.keys()))

    # 2. If Counter-Strike is included, scrape and merge HLTV matches
    if disc in ("all", "counterstrike"):
        try:
            hltv_matches = await hltv_scraper.get_matches(selected_date=date)
            if hltv_matches:
                cs_liquipedia = [m for m in scraped_matches if m.discipline == "counterstrike"]
                other_liquipedia = [m for m in scraped_matches if m.discipline != "counterstrike"]
                merged_cs = hltv_scraper.merge_with_liquipedia(cs_liquipedia, hltv_matches)
                scraped_matches = other_liquipedia + merged_cs
        except Exception as e:
            print(f"HLTV merge notice: {e}")

    # 3. Process matches through 5-minute resilience cache manager
    active_matches = esports_cache_manager.process_matches(scraped_matches, discipline_filter=disc)

    # 4. Compute counts before status/search filters
    counts = {"all": 0, "live": 0, "upcoming": 0, "finished": 0, "draw": 0}
    discipline_counts: Dict[str, int] = {}

    for m in active_matches:
        counts["all"] += 1
        st = m.status if m.status in counts else "upcoming"
        counts[st] += 1
        if m.is_draw:
            counts["draw"] += 1
        d_key = m.discipline
        discipline_counts[d_key] = discipline_counts.get(d_key, 0) + 1

    # 5. Apply Status filter
    filtered = active_matches
    if status and status != "all":
        if status == "draw":
            filtered = [m for m in filtered if m.is_draw]
        else:
            filtered = [m for m in filtered if m.status == status]

    # 6. Apply Date filter
    if date:
        filtered = [m for m in filtered if m.start_date and m.start_date.startswith(date)]

    # 7. Apply Search filter
    if search and search.strip():
        q = search.strip().lower()
        filtered = [
            m for m in filtered
            if q in (m.team1_name or "").lower()
            or q in (m.team1_short or "").lower()
            or q in (m.team2_name or "").lower()
            or q in (m.team2_short or "").lower()
            or q in (m.tournament_name or "").lower()
            or q in (m.discipline_name or "").lower()
        ]

    return EsportsResponse(
        total=len(filtered),
        counts=counts,
        discipline_counts=discipline_counts,
        discipline_filter=disc,
        status_filter=status,
        date_filter=date,
        search=search,
        matches=filtered,
    )


@app.get("/api/esports/removed-matches", response_model=EsportsRemovedMatchesResponse)
async def get_esports_removed_matches(
    discipline: Optional[str] = Query(None, description="Discipline filter"),
):
    """Retrieve history of removed esports matches."""
    items = esports_cache_manager.get_removed_matches(discipline=discipline)
    return EsportsRemovedMatchesResponse(total=len(items), matches=items)


@app.post("/api/esports/removed-matches/clear")
async def clear_esports_removed_matches():
    """Clear all removed esports matches history."""
    esports_cache_manager.clear_removed()
    return {"status": "success", "message": "Esports removed matches history cleared"}


@app.post("/api/esports/removed-matches/restore/{match_id}")
async def restore_esports_removed_match(match_id: str):
    """Restore an esports match from removed archive back to active monitor."""
    success = esports_cache_manager.restore_match(match_id)
    if not success:
        raise HTTPException(status_code=404, detail="Match not found in removed archive")
    return {"status": "success", "message": f"Match {match_id} restored"}


@app.get("/api/hltv/config")
async def get_hltv_config():
    """Get HLTV cookie configuration status."""
    return {
        "cookie_set": bool(hltv_scraper.cookie_header),
        "cookies_count": len(hltv_scraper.cookies_dict),
        "cookie_names": list(hltv_scraper.cookies_dict.keys()),
        "cookie_snippet": (
            hltv_scraper.cookie_header[:40] + "..." if len(hltv_scraper.cookie_header) > 40 else hltv_scraper.cookie_header
        ),
    }


@app.post("/api/hltv/config")
async def set_hltv_config(payload: HLTVConfigUpdate):
    """Update HLTV cookie (supports JSON array from extension or string)."""
    val = payload.cookie if payload.cookie is not None else payload.raw_cookie
    count, names = hltv_scraper.set_cookie(val)
    return {
        "status": "success",
        "cookies_count": count,
        "cookie_names": names,
        "cookie_set": bool(hltv_scraper.cookie_header),
    }


@app.get("/api/liquipedia/config")
async def get_liquipedia_config():
    """Get Liquipedia cookie configuration status."""
    return {
        "cookie_set": bool(liquipedia_scraper.cookie_header),
        "cookies_count": len(liquipedia_scraper.cookies_dict),
        "cookie_names": list(liquipedia_scraper.cookies_dict.keys()),
        "cookie_snippet": (
            liquipedia_scraper.cookie_header[:40] + "..." if len(liquipedia_scraper.cookie_header) > 40 else liquipedia_scraper.cookie_header
        ),
    }


@app.post("/api/liquipedia/config")
async def set_liquipedia_config(payload: LiquipediaConfigUpdate):
    """Update Liquipedia cookie (supports JSON array from extension or header string)."""
    val = payload.cookie if payload.cookie is not None else payload.raw_cookie
    count, names = liquipedia_scraper.set_cookie(val)
    return {
        "status": "success",
        "cookies_count": count,
        "cookie_names": names,
        "cookie_set": bool(liquipedia_scraper.cookie_header),
    }



@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "online",
        "services": {
            "setka_cup": {
                "cached_keys": list(scraper._cache.keys()),
                "known_halls": len(scraper._halls_map),
                "known_periods": len(scraper._periods_map),
            },
            "tt_cup": {
                "captcha_required": ttcup_scraper.captcha_detected,
                "cached_tournaments": len(ttcup_scraper._tournaments_cache),
                "cached_schedules": len(ttcup_scraper._schedule_cache),
            },
        },
    }


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the dashboard single-page interface."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse(
        "<h1>Dashboard is loading... Please ensure static/index.html is created.</h1>"
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Setka Cup Real-Time Monitor on http://localhost:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
