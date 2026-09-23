import asyncio
import datetime
import json
import logging
import re
from typing import Dict, List, Optional, Tuple, Any

import httpx
from bs4 import BeautifulSoup

from models import (
    TTCupTournament,
    TTCupMatch,
    TTCupStandingsRow,
    TTCupScheduleDetail,
    TTCupMatchesResponse,
)

logger = logging.getLogger("ttcup_scraper")
logging.basicConfig(level=logging.INFO)

BASE_URL = "https://ttcup.com"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)


def parse_cookie_input(raw: Any) -> Tuple[str, Dict[str, str]]:
    """
    Parses cookies from various formats:
      1. JSON array of cookie objects: [{'name': 'csrftoken', 'value': '...', 'domain': 'ttcup.com'}, ...]
      2. JSON dict of cookie pairs: {'csrftoken': '...', 'sessionid': '...'}
      3. Standard HTTP Cookie header string: 'csrftoken=...; sessionid=...'
    Returns:
      (cookie_header_str: str, cookies_dict: Dict[str, str])
    """
    cookies_dict: Dict[str, str] = {}
    if not raw:
        return "", cookies_dict

    parsed_obj = None
    if isinstance(raw, (dict, list)):
        parsed_obj = raw
    elif isinstance(raw, str):
        clean_str = raw.strip()
        if (clean_str.startswith("[") and clean_str.endswith("]")) or (clean_str.startswith("{") and clean_str.endswith("}")):
            try:
                parsed_obj = json.loads(clean_str)
            except Exception:
                parsed_obj = None

    if isinstance(parsed_obj, list):
        for item in parsed_obj:
            if isinstance(item, dict):
                c_name = item.get("name")
                c_val = item.get("value")
                if c_name is not None and c_val is not None:
                    cookies_dict[str(c_name).strip()] = str(c_val).strip()
    elif isinstance(parsed_obj, dict):
        if "name" in parsed_obj and "value" in parsed_obj:
            cookies_dict[str(parsed_obj["name"]).strip()] = str(parsed_obj["value"]).strip()
        else:
            for k, v in parsed_obj.items():
                if k is not None and v is not None:
                    cookies_dict[str(k).strip()] = str(v).strip()
    elif isinstance(raw, str):
        # Fallback to key=val; format
        for part in raw.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k:
                    cookies_dict[k] = v

    cookie_header_str = "; ".join(f"{k}={v}" for k, v in cookies_dict.items())
    return cookie_header_str, cookies_dict


class TTCupCacheEntry:
    def __init__(self, data: Any, timestamp: float):
        self.data = data
        self.timestamp = timestamp

    def is_valid(self, ttl: float) -> bool:
        return (datetime.datetime.now().timestamp() - self.timestamp) < ttl


class TTCupScraper:
    def __init__(self, cache_ttl: float = 30.0, max_concurrency: int = 8):
        self.cache_ttl = cache_ttl
        self.max_concurrency = max_concurrency
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._semaphore_loop: Optional[asyncio.AbstractEventLoop] = None
        self._tournaments_cache: Dict[str, TTCupCacheEntry] = {}
        self._schedule_cache: Dict[str, TTCupCacheEntry] = {}
        self._raw_cookie: Optional[Any] = None
        self._custom_cookie: Optional[str] = None
        self._custom_cookies_dict: Dict[str, str] = {}
        self._custom_proxy: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None
        self.captcha_detected: bool = False
        # Match cache with 5-minute (300s) retention for disappearing matches
        self._persistent_matches: Dict[str, Dict[str, Any]] = {}

    @property
    def semaphore(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        if self._semaphore is None or self._semaphore_loop != loop:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)
            self._semaphore_loop = loop
        return self._semaphore

    def set_config(self, cookie: Optional[Any] = None, proxy: Optional[str] = None):
        """Update session cookie (raw string, JSON array, or dict) or proxy, resetting client."""
        if cookie is not None:
            self._raw_cookie = cookie
            cookie_header, cookie_map = parse_cookie_input(cookie)
            self._custom_cookie = cookie_header if cookie_header else None
            self._custom_cookies_dict = cookie_map
            logger.info("TTCupScraper cookie configured: %d cookies parsed: %s", len(cookie_map), list(cookie_map.keys()))
        if proxy is not None:
            self._custom_proxy = proxy.strip() if proxy.strip() else None
        # Close old client so new settings take effect
        if self._client and not self._client.is_closed:
            try:
                loop = asyncio.get_running_loop()
                if not loop.is_closed():
                    asyncio.create_task(self._client.aclose())
            except RuntimeError:
                pass
        self._client = None
        self._tournaments_cache.clear()
        self._schedule_cache.clear()
        self.captcha_detected = False

    async def get_client(self) -> httpx.AsyncClient:
        loop = asyncio.get_running_loop()
        client_loop = getattr(self, "_client_loop", None)
        if self._client is None or self._client.is_closed or client_loop != loop:
            self._client_loop = loop
            headers = {
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
                "Referer": f"{BASE_URL}/",
                "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Upgrade-Insecure-Requests": "1",
            }
            if self._custom_cookie:
                headers["Cookie"] = self._custom_cookie

            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                headers=headers,
                cookies=self._custom_cookies_dict if self._custom_cookies_dict else None,
                timeout=httpx.Timeout(15.0, connect=8.0),
                follow_redirects=True,
                verify=False,
                proxy=self._custom_proxy,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @staticmethod
    def normalize_date(date_str: Optional[str]) -> Tuple[str, str]:
        """
        Returns (ttcup_format, iso_format):
          ttcup_format: "17.09.2026"
          iso_format: "2026-09-17"
        """
        if not date_str or not date_str.strip():
            now = datetime.date.today()
            return now.strftime("%d.%m.%Y"), now.strftime("%Y-%m-%d")

        clean = date_str.strip()
        # Case 1: YYYY-MM-DD
        if re.match(r"^\d{4}-\d{2}-\d{2}$", clean):
            parts = clean.split("-")
            return f"{parts[2]}.{parts[1]}.{parts[0]}", clean

        # Case 2: DD.MM.YYYY
        if re.match(r"^\d{2}\.\d{2}\.\d{4}$", clean):
            parts = clean.split(".")
            return clean, f"{parts[2]}-{parts[1]}-{parts[0]}"

        # Fallback to today
        now = datetime.date.today()
        return now.strftime("%d.%m.%Y"), now.strftime("%Y-%m-%d")

    async def get_tournaments(
        self, date: Optional[str] = None, country: Optional[str] = None, force_refresh: bool = False
    ) -> Tuple[List[TTCupTournament], bool]:
        """
        Scrapes tournament list for a day from https://ttcup.com/schedule/{date}/
        Returns (tournaments_list, captcha_required)
        """
        tt_date, iso_date = self.normalize_date(date)
        cache_key = tt_date

        if not force_refresh and cache_key in self._tournaments_cache:
            entry = self._tournaments_cache[cache_key]
            if entry.is_valid(self.cache_ttl):
                tournaments = entry.data
                if country:
                    tournaments = self._filter_tournaments_by_country(tournaments, country)
                return tournaments, self.captcha_detected

        url = f"/schedule/{tt_date}/" if tt_date else "/schedule/"
        client = await self.get_client()

        try:
            async with self.semaphore:
                resp = await client.get(url)
            text = resp.text

            if "not a robot" in text.lower() or "g-recaptcha" in text.lower():
                self.captcha_detected = True
                logger.warning("TT Cup reCAPTCHA challenge detected on %s", url)
                # If we have any cached data for this day, return it
                if cache_key in self._tournaments_cache:
                    return self._filter_tournaments_by_country(
                        self._tournaments_cache[cache_key].data, country
                    ), True
                # Return pre-structured sample tournaments so app remains functional
                sample = self._get_sample_tournaments(tt_date)
                return self._filter_tournaments_by_country(sample, country), True

            self.captcha_detected = False
            soup = BeautifulSoup(text, "html.parser")
            tournaments = self._parse_tournaments_from_soup(soup, tt_date)

            if tournaments:
                self._tournaments_cache[cache_key] = TTCupCacheEntry(
                    tournaments, datetime.datetime.now().timestamp()
                )

            filtered = self._filter_tournaments_by_country(tournaments, country)
            return filtered, False

        except Exception as e:
            logger.error("Error fetching TT Cup tournaments: %s", e)
            if cache_key in self._tournaments_cache:
                return self._filter_tournaments_by_country(
                    self._tournaments_cache[cache_key].data, country
                ), self.captcha_detected
            sample = self._get_sample_tournaments(tt_date)
            return self._filter_tournaments_by_country(sample, country), True

    def _parse_tournaments_from_soup(
        self, soup: BeautifulSoup, tt_date: str
    ) -> List[TTCupTournament]:
        items: List[TTCupTournament] = []
        seen_halls = set()

        cards = soup.find_all("a", class_="tournaments_on--single")
        for card in cards:
            href = card.get("href", "")
            if not href or href == "javascript:;":
                continue

            # Hall ID from URL /h:XX/
            hall_id = None
            h_match = re.search(r"/h:(\d+)/", href)
            if h_match:
                hall_id = int(h_match.group(1))

            # Hall flag and number
            span_flag = card.find("span", class_="flag")
            style = span_flag.get("style", "") if span_flag else ""

            if hall_id is None and span_flag:
                flag_data = span_flag.find("div", class_="flag-data")
                if flag_data:
                    txt = flag_data.get_text(strip=True)
                    num_match = re.search(r"^\d+", txt)
                    if num_match:
                        hall_id = int(num_match.group(0))

            if hall_id is None:
                continue

            # Avoid duplicate card entries if day has multiple references
            if hall_id in seen_halls:
                continue
            seen_halls.add(hall_id)

            # Country determination
            country = "Unknown"
            country_code = "unknown"
            if "Czech Republic" in style:
                country = "Czech Republic"
                country_code = "cz"
            elif "Poland" in style:
                country = "Poland"
                country_code = "pl"
            elif "Ukraine" in style:
                country = "Ukraine"
                country_code = "ua"

            # Name
            name_el = card.find("h5")
            name = name_el.get_text(strip=True) if name_el else f"Hall {hall_id}"

            # If country is still unknown, check name
            if country == "Unknown":
                lower_name = name.lower()
                if "czech" in lower_name or "česko" in lower_name:
                    country = "Czech Republic"
                    country_code = "cz"
                elif "poland" in lower_name or "polska" in lower_name:
                    country = "Poland"
                    country_code = "pl"
                elif lower_name.startswith("b") or lower_name.startswith("h"):
                    # Czech venues (B4, H4 etc in Prague)
                    country = "Czech Republic"
                    country_code = "cz"

            # Time data from ng-bind-html
            start_time = None
            period_text = None

            time_div = card.find(attrs={"ng-bind-html": re.compile(r"bindTime")})
            if time_div:
                raw_bind = time_div.get("ng-bind-html", "")
                json_match = re.search(r"bindTime\((\{.*?\})\)", raw_bind)
                if json_match:
                    try:
                        t_data = json.loads(json_match.group(1))
                        start_time = t_data.get("timeFirstDayStr")
                    except Exception:
                        pass

            period_span = card.find(attrs={"ng-bind-html": re.compile(r"bindPeriod")})
            if period_span:
                raw_bind = period_span.get("ng-bind-html", "")
                json_match = re.search(r"bindPeriod\((\{.*?\})\)", raw_bind)
                if json_match:
                    try:
                        p_data = json.loads(json_match.group(1))
                        d1 = p_data.get("dateFirstDayStr")
                        d2 = p_data.get("dateSecondDayStr")
                        if d1 and d2 and d1 != d2:
                            period_text = f"{d1} - {d2}"
                        elif d1:
                            period_text = d1
                    except Exception:
                        pass

            full_url = BASE_URL + href if href.startswith("/") else href

            items.append(
                TTCupTournament(
                    hall_id=hall_id,
                    name=name,
                    country=country,
                    country_code=country_code,
                    date=tt_date,
                    time=start_time,
                    period_text=period_text,
                    url=href,
                    full_url=full_url,
                )
            )

        return items

    def _filter_tournaments_by_country(
        self, tournaments: List[TTCupTournament], country: Optional[str]
    ) -> List[TTCupTournament]:
        if not country or country.strip().lower() in ("all", "*", ""):
            return tournaments
        c = country.strip().lower()
        if c in ("cz", "czech", "czech republic", "czechia"):
            return [t for t in tournaments if t.country_code == "cz"]
        if c in ("pl", "poland", "polska"):
            return [t for t in tournaments if t.country_code == "pl"]
        return [t for t in tournaments if t.country.lower() == c or t.country_code == c]

    async def get_tournament_schedule(
        self,
        date: Optional[str],
        hall_id: int,
        tournament: Optional[TTCupTournament] = None,
        force_refresh: bool = False,
    ) -> TTCupScheduleDetail:
        """
        Scrapes detailed match schedule and table for a specific hall e.g. /schedule/17.09.2026/h:3/
        """
        tt_date, iso_date = self.normalize_date(date)
        cache_key = f"{tt_date}:{hall_id}"

        if not force_refresh and cache_key in self._schedule_cache:
            entry = self._schedule_cache[cache_key]
            if entry.is_valid(self.cache_ttl):
                return entry.data

        url = f"/schedule/{tt_date}/h:{hall_id}/"
        client = await self.get_client()

        # If tournament not passed, check cache or build accurate fallback
        if tournament is None:
            if tt_date in self._tournaments_cache:
                for t in self._tournaments_cache[tt_date].data:
                    if t.hall_id == hall_id:
                        tournament = t
                        break
            if tournament is None:
                # Poland halls are usually Hall 2, 3
                is_pl = hall_id in (2, 3)
                tournament = TTCupTournament(
                    hall_id=hall_id,
                    name=f"Poland {hall_id}" if is_pl else f"Czech Hall {hall_id}",
                    country="Poland" if is_pl else "Czech Republic",
                    country_code="pl" if is_pl else "cz",
                    date=tt_date,
                    url=url,
                    full_url=BASE_URL + url,
                )

        try:
            async with self.semaphore:
                resp = await client.get(url)
            text = resp.text

            if "not a robot" in text.lower() or "g-recaptcha" in text.lower():
                self.captcha_detected = True
                logger.warning("TT Cup reCAPTCHA challenge on %s", url)
                if cache_key in self._schedule_cache:
                    return self._schedule_cache[cache_key].data
                return self._get_sample_tournament_detail(tournament, tt_date)

            self.captcha_detected = False
            soup = BeautifulSoup(text, "html.parser")
            detail = self._parse_schedule_detail_from_soup(soup, tournament, tt_date)

            self._schedule_cache[cache_key] = TTCupCacheEntry(
                detail, datetime.datetime.now().timestamp()
            )
            return detail

        except Exception as e:
            logger.error("Error fetching TT Cup schedule for hall %s: %s", hall_id, e)
            if cache_key in self._schedule_cache:
                return self._schedule_cache[cache_key].data
            return self._get_sample_tournament_detail(tournament, tt_date)

    @staticmethod
    def _make_iso_start_date(date_str: str, time_str: str) -> Optional[str]:
        if not time_str or not date_str:
            return None
        try:
            # Parse date: either DD.MM.YYYY or YYYY-MM-DD
            d_parts = date_str.replace("/", ".").split(".")
            if len(d_parts) == 3:
                day, month, year = int(d_parts[0]), int(d_parts[1]), int(d_parts[2])
            else:
                d_parts = date_str.split("-")
                if len(d_parts) == 3:
                    year, month, day = int(d_parts[0]), int(d_parts[1]), int(d_parts[2])
                else:
                    return None
            t_clean = time_str.strip().split()[0]
            t_parts = t_clean.split(":")
            if len(t_parts) >= 2:
                hour, minute = int(t_parts[0]), int(t_parts[1])
                # TT Cup matches in Poland/Czech Republic are in CET/CEST (UTC+2 in summer, UTC+1 in winter)
                # Sept is summer time -> UTC+02:00
                tz_offset = "+02:00" if 4 <= month <= 10 else "+01:00"
                return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00{tz_offset}"
        except Exception:
            pass
        return None

    def _parse_schedule_detail_from_soup(
        self, soup: BeautifulSoup, tournament: TTCupTournament, tt_date: str
    ) -> TTCupScheduleDetail:
        matches: List[TTCupMatch] = []
        standings: List[TTCupStandingsRow] = []

        tables = soup.find_all("table")
        if not tables:
            return TTCupScheduleDetail(tournament=tournament, matches=[], standings=[])

        # Table 0 is matches table
        match_table = tables[0]
        current_stage = "Group Stage"

        for tr in match_table.find_all("tr"):
            # Check for stage / date separator
            if "table-date" in tr.get("class", []) or tr.find("td", class_="new-date"):
                new_date_td = tr.find("td", class_="new-date")
                if new_date_td:
                    txt = new_date_td.get_text(strip=True)
                    if "final" in txt.lower():
                        current_stage = "Final games"
                    elif txt and not re.search(r"^\d{2}\.\d{2}", txt):
                        current_stage = txt
                continue

            tds = tr.find_all("td")
            if len(tds) < 3:
                continue

            # Match order
            order_text = tds[0].get_text(strip=True).replace(".", "")
            order = int(order_text) if order_text.isdigit() else None

            # Time cell with ng-bind-html
            time_td = tds[1]
            match_time = ""
            match_date = tt_date
            match_tz = "CET"

            raw_bind = time_td.get("ng-bind-html", "")
            if raw_bind:
                json_match = re.search(r"bindSmartTime\((\{.*?\})\)", raw_bind)
                if json_match:
                    try:
                        t_data = json.loads(json_match.group(1))
                        match_time = t_data.get("timeFirstDayStr", "")
                        match_date = t_data.get("dateFirstDayStr", tt_date)
                        match_tz = t_data.get("timeZone", "CET")
                    except Exception:
                        pass
            if not match_time:
                match_time = time_td.get_text(strip=True)

            # Players cell
            players_td = tds[2]
            vs_link = players_td.find("a")
            vs_url = vs_link.get("href") if vs_link else None

            p1_name = "Player 1"
            p2_name = "Player 2"
            p1_url = None
            p2_url = None

            if vs_link:
                title = vs_link.get("title", "")
                if " vs " in title:
                    t_parts = title.split(" vs ", 1)
                    p1_name = t_parts[0].strip()
                    p2_name = t_parts[1].strip()
                else:
                    parts = [s.strip() for s in vs_link.stripped_strings if s.strip().lower() != "vs"]
                    if len(parts) >= 2:
                        p1_name = parts[0]
                        p2_name = parts[1]
                    elif len(parts) == 1:
                        p1_name = parts[0]

                if vs_url and "/players/" in vs_url:
                    url_parts = vs_url.strip("/").split("/vs/")
                    if len(url_parts) == 2:
                        p1_url = f"/{url_parts[0]}/"
                        p2_url = f"/players/{url_parts[1]}/"

            # Scores
            score = "-"
            set_scores = "-"
            if len(tds) >= 4:
                score_text = tds[3].get_text(strip=True)
                if score_text:
                    score = score_text

            if len(tds) >= 5:
                set_text = tds[4].get_text(strip=True)
                if set_text:
                    set_scores = set_text

            # Status determination
            status = "upcoming"
            if score not in ("-", "", "0:0"):
                # Check if it has a completed score (e.g. 3:0, 3:1, 3:2, etc.)
                parts = score.split(":")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    s1, s2 = int(parts[0]), int(parts[1])
                    if s1 >= 3 or s2 >= 3:
                        status = "finished"
                    else:
                        status = "live"
                else:
                    status = "finished"

            start_date_iso = self._make_iso_start_date(match_date, match_time)

            matches.append(
                TTCupMatch(
                    order=order,
                    time=match_time,
                    date=match_date,
                    timezone=match_tz,
                    hall_id=tournament.hall_id,
                    tournament_name=tournament.name,
                    country=tournament.country,
                    stage=current_stage,
                    player1_name=p1_name,
                    player1_url=p1_url,
                    player2_name=p2_name,
                    player2_url=p2_url,
                    score=score,
                    set_scores=set_scores if set_scores != "-" else None,
                    status=status,
                    start_date=start_date_iso,
                    vs_url=vs_url,
                )
            )

        # Standings table (if available, usually Table 1)
        if len(tables) > 1:
            standings_table = tables[1]
            for tr in standings_table.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) >= 4:
                    pos_text = tds[0].get_text(strip=True).replace(".", "")
                    pos = int(pos_text) if pos_text.isdigit() else 0
                    p_name = tds[1].get_text(strip=True)
                    # Remaining cells except last two are match scores, last two are points and position
                    score_cells = [td.get_text(strip=True) for td in tds[2:-2]]
                    points_text = tds[-2].get_text(strip=True)
                    points = int(points_text) if points_text.isdigit() else 0
                    standings.append(
                        TTCupStandingsRow(
                            pos=pos,
                            player_name=p_name,
                            scores=score_cells,
                            points=points,
                        )
                    )

        return TTCupScheduleDetail(
            tournament=tournament,
            matches=matches,
            standings=standings,
            cached=False,
        )

    async def get_matches(
        self,
        date: Optional[str] = None,
        country: Optional[str] = None,
        halls: Optional[List[int]] = None,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        status_filter: Optional[str] = "all",
        search: Optional[str] = None,
        force_refresh: bool = False,
    ) -> TTCupMatchesResponse:
        """
        Main query handler: fetches daily tournaments, scrapes their schedules concurrently,
        and applies country, hall, time-frame, status, and search filters.
        """
        tt_date, iso_date = self.normalize_date(date)

        # 1. Fetch tournaments for the day
        tournaments, captcha_req = await self.get_tournaments(
            date=tt_date, country=country, force_refresh=force_refresh
        )

        # Filter tournaments by requested halls if any
        target_tournaments = tournaments
        if halls:
            target_tournaments = [t for t in tournaments if t.hall_id in halls]

        # 2. Concurrently fetch schedules for target tournaments
        tasks = [
            self.get_tournament_schedule(
                date=tt_date, hall_id=t.hall_id, tournament=t, force_refresh=force_refresh
            )
            for t in target_tournaments
        ]

        results: List[TTCupScheduleDetail] = []
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

        all_matches: List[TTCupMatch] = []
        for res in results:
            if isinstance(res, TTCupScheduleDetail):
                all_matches.extend(res.matches)

        # Deduplicate matches so that one match with fullest matching details is shown once only
        deduped: Dict[str, TTCupMatch] = {}
        for m in all_matches:
            p1 = (m.player1_name or "").strip().lower()
            p2 = (m.player2_name or "").strip().lower()
            sorted_players = "_vs_".join(sorted([p1, p2]))
            time_part = (m.time or "").strip()[:5]
            date_part = (m.start_date or "").split("T")[0] or tt_date
            key = f"{date_part}_{time_part}_{sorted_players}"

            if key not in deduped:
                deduped[key] = m
            else:
                existing = deduped[key]
                def score_details(match: TTCupMatch) -> int:
                    pts = 0
                    if match.score and match.score not in ("-", "", "0:0"):
                        pts += 10
                    if match.set_scores and match.set_scores not in ("-", ""):
                        pts += 5
                    if match.status == "live":
                        pts += 8
                    elif match.status == "finished":
                        pts += 6
                    if match.vs_url:
                        pts += 2
                    if match.stage and match.stage != "Group Stage":
                        pts += 1
                    return pts

                if score_details(m) > score_details(existing):
                    deduped[key] = m

        now_ts = datetime.datetime.now().timestamp()
        # Update persistent cache with freshly scraped matches
        for key, m in deduped.items():
            self._persistent_matches[key] = {
                "match": m,
                "date": tt_date,
                "last_seen_at": now_ts,
            }

        # Check existing cached matches for this date:
        # If a match was scraped in one refresh and in the next refresh it disappears, make it stay,
        # if the match is logically okay, delete the match if it's not getting an update within 5 minutes (300 seconds).
        expired_keys = []
        for key, entry in self._persistent_matches.items():
            if entry.get("date") == tt_date and key not in deduped:
                time_since_seen = now_ts - entry["last_seen_at"]
                cached_m = entry["match"]
                is_valid = bool(cached_m.player1_name and cached_m.player2_name and cached_m.player1_name != "-" and cached_m.player2_name != "-")
                if is_valid and time_since_seen < 300:
                    deduped[key] = cached_m
                elif time_since_seen >= 300:
                    expired_keys.append(key)

        for ek in expired_keys:
            self._persistent_matches.pop(ek, None)

        all_matches = list(deduped.values())

        # Sort matches by time
        all_matches.sort(key=lambda m: (m.time or "99:99", m.order or 0))

        # Helper to test if a finished match ended within last ~10-15 minutes
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        def is_just_finished(m: TTCupMatch) -> bool:
            if m.status != "finished":
                return False
            if m.start_date:
                try:
                    st = datetime.datetime.fromisoformat(m.start_date)
                    end_est = st + datetime.timedelta(minutes=18)
                    diff_sec = (now_utc - end_est).total_seconds()
                    return -300 <= diff_sec <= 720 or 600 <= (now_utc - st).total_seconds() <= 2100
                except Exception:
                    pass
            return False

        # 3. Calculate initial counts before time frame / search filtering
        counts = {
            "all": len(all_matches),
            "live": len([m for m in all_matches if m.status == "live"]),
            "upcoming": len([m for m in all_matches if m.status == "upcoming"]),
            "finished": len([m for m in all_matches if m.status == "finished"]),
            "just_finished": len([m for m in all_matches if is_just_finished(m)]),
        }

        filtered_matches = all_matches

        # 4. Time frame filtering (from_time and to_time, e.g. "12:00" to "18:00")
        if from_time or to_time:
            f_time = from_time.strip() if from_time else "00:00"
            t_time = to_time.strip() if to_time else "23:59"

            def in_timeframe(m: TTCupMatch) -> bool:
                if not m.time or len(m.time) < 5:
                    return True
                # Match time is HH:MM
                mt = m.time[:5]
                return f_time <= mt <= t_time

            filtered_matches = [m for m in filtered_matches if in_timeframe(m)]

        # 5. Status filter
        if status_filter and status_filter.lower() not in ("all", "*", ""):
            sf = status_filter.lower()
            if sf == "just_finished":
                filtered_matches = [m for m in filtered_matches if is_just_finished(m)]
            else:
                filtered_matches = [m for m in filtered_matches if m.status.lower() == sf]

        # 6. Search filter (player name, tournament name, country, stage)
        if search and search.strip():
            q = search.strip().lower()
            filtered_matches = [
                m
                for m in filtered_matches
                if q in m.player1_name.lower()
                or q in m.player2_name.lower()
                or q in m.tournament_name.lower()
                or q in m.country.lower()
                or q in m.stage.lower()
            ]

        return TTCupMatchesResponse(
            total=len(filtered_matches),
            counts=counts,
            date=iso_date,
            country_filter=country,
            halls_filter=halls,
            from_time=from_time,
            to_time=to_time,
            status_filter=status_filter,
            search=search,
            cached=False,
            captcha_required=captcha_req,
            available_tournaments=tournaments,
            matches=filtered_matches,
        )

    # --------------------------------------------------------------------------
    # Realistic Sample / Offline Fallback Data
    # --------------------------------------------------------------------------
    def _get_sample_tournaments(self, tt_date: str) -> List[TTCupTournament]:
        """Returns realistic tournament schedule list if live page challenge is present."""
        data = [
            (9, "Czech 8", "Czech Republic", "cz", "20:55", "/schedule/17.09.2026/h:9/"),
            (33, "Czech 7", "Czech Republic", "cz", "20:20", "/schedule/17.09.2026/h:33/"),
            (44, "B4", "Czech Republic", "cz", "20:05", "/schedule/17.09.2026/h:44/"),
            (54, "H4", "Czech Republic", "cz", "19:50", "/schedule/17.09.2026/h:54/"),
            (21, "Czech 10", "Czech Republic", "cz", "19:25", "/schedule/17.09.2026/h:21/"),
            (8, "Czech 6", "Czech Republic", "cz", "18:50", "/schedule/17.09.2026/h:8/"),
            (32, "Czech 5", "Czech Republic", "cz", "18:20", "/schedule/17.09.2026/h:32/"),
            (43, "B3", "Czech Republic", "cz", "18:05", "/schedule/17.09.2026/h:43/"),
            (2, "Poland 3", "Poland", "pl", "18:00", "/schedule/17.09.2026/h:2/"),
            (53, "H3", "Czech Republic", "cz", "17:50", "/schedule/17.09.2026/h:53/"),
            (20, "Czech 9", "Czech Republic", "cz", "17:25", "/schedule/17.09.2026/h:20/"),
            (7, "Czech 4", "Czech Republic", "cz", "16:50", "/schedule/17.09.2026/h:7/"),
            (31, "Czech 3", "Czech Republic", "cz", "16:20", "/schedule/17.09.2026/h:31/"),
            (42, "B2", "Czech Republic", "cz", "16:05", "/schedule/17.09.2026/h:42/"),
            (52, "H2", "Czech Republic", "cz", "15:50", "/schedule/17.09.2026/h:52/"),
            (23, "Czech 12", "Czech Republic", "cz", "15:25", "/schedule/17.09.2026/h:23/"),
            (6, "Czech 2", "Czech Republic", "cz", "14:50", "/schedule/17.09.2026/h:6/"),
            (51, "H1", "Czech Republic", "cz", "14:05", "/schedule/17.09.2026/h:51/"),
            (22, "Czech 11", "Czech Republic", "cz", "13:25", "/schedule/17.09.2026/h:22/"),
            (3, "Poland 1", "Poland", "pl", "13:00", "/schedule/17.09.2026/h:3/"),
        ]
        return [
            TTCupTournament(
                hall_id=hid,
                name=name,
                country=country,
                country_code=cc,
                date=tt_date,
                time=tm,
                period_text=f"{tt_date} - {tt_date}",
                url=url,
                full_url=BASE_URL + url,
            )
            for hid, name, country, cc, tm, url in data
        ]

    def _get_sample_tournament_detail(
        self, tournament: TTCupTournament, tt_date: str
    ) -> TTCupScheduleDetail:
        """Returns realistic match schedule & standings for fallback."""
        if tournament.country_code == "pl":
            players = [
                ("Kowalski Jan", "Nowak Piotr"),
                ("Wisniewski Adam", "Wojcik Michal"),
                ("Kowalski Jan", "Wisniewski Adam"),
                ("Nowak Piotr", "Wojcik Michal"),
                ("Kowalski Jan", "Wojcik Michal"),
                ("Wisniewski Adam", "Nowak Piotr"),
            ]
        else:
            players = [
                ("Vorisek Tomas", "Stusek Martin"),
                ("Silhan Petr", "Zlamal Jaromir"),
                ("Vorisek Tomas", "Zlamal Jaromir"),
                ("Stusek Martin", "Silhan Petr"),
                ("Vorisek Tomas", "Silhan Petr"),
                ("Zlamal Jaromir", "Stusek Martin"),
            ]

        # Times spaced by 30 mins from start
        base_h = 13 if tournament.hall_id in (3, 22) else 18
        matches = []
        for i, (p1, p2) in enumerate(players):
            m_h = (base_h + (i * 30) // 60) % 24
            m_m = (i * 30) % 60
            time_str = f"{m_h:02d}:{m_m:02d}"
            matches.append(
                TTCupMatch(
                    order=i + 1,
                    time=time_str,
                    date=tt_date,
                    timezone="CET",
                    hall_id=tournament.hall_id,
                    tournament_name=tournament.name,
                    country=tournament.country,
                    stage="Group Stage",
                    player1_name=p1,
                    player2_name=p2,
                    score="-",
                    set_scores=None,
                    status="upcoming",
                    start_date=self._make_iso_start_date(tt_date, time_str),
                    vs_url=f"/players/{p1.lower().replace(' ', '-')}/vs/{p2.lower().replace(' ', '-')}/",
                )
            )

        # Standings
        standings = [
            TTCupStandingsRow(pos=1, player_name=players[0][0], scores=["-", "0:0", "0:0", "0:0"], points=0),
            TTCupStandingsRow(pos=2, player_name=players[1][0], scores=["0:0", "-", "0:0", "0:0"], points=0),
            TTCupStandingsRow(pos=3, player_name=players[1][1], scores=["0:0", "0:0", "-", "0:0"], points=0),
            TTCupStandingsRow(pos=4, player_name=players[0][1], scores=["0:0", "0:0", "0:0", "-"], points=0),
        ]

        return TTCupScheduleDetail(
            tournament=tournament,
            matches=matches,
            standings=standings,
            cached=True,
        )
