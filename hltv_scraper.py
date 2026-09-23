"""
HLTV Scraper module.
Scrapes Counter-Strike matches from https://www.hltv.org/matches
Supports:
- Date selection: selectedDate=YYYY-MM-DD
- Cookie management (JSON format / header string) via hltv_cookie.txt or UI configuration
- Extracting team names, initials, format (BO1/BO3), tournament name, time, and live streams
- Merging missing matches with Liquipedia Counter-Strike matches
"""

import datetime
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import httpx

from models import EsportsMatchItem

logger = logging.getLogger("hltv_scraper")
logging.basicConfig(level=logging.INFO)

HLTV_COOKIE_FILE = "hltv_cookie.txt"
BASE_URL = "https://www.hltv.org"


def parse_hltv_cookie_input(raw_input: Any) -> tuple[str, Dict[str, str]]:
    """Parse cookie input from JSON array, JSON dict, or raw header string."""
    if not raw_input:
        return "", {}

    cookies_dict: Dict[str, str] = {}

    if isinstance(raw_input, list):
        for item in raw_input:
            if isinstance(item, dict) and "name" in item and "value" in item:
                cookies_dict[item["name"]] = str(item["value"])
    elif isinstance(raw_input, dict):
        for k, v in raw_input.items():
            cookies_dict[str(k)] = str(v)
    elif isinstance(raw_input, str):
        cleaned = raw_input.strip()
        if (cleaned.startswith("[") and cleaned.endswith("]")) or (cleaned.startswith("{") and cleaned.endswith("}")):
            try:
                parsed_json = json.loads(cleaned)
                return parse_hltv_cookie_input(parsed_json)
            except Exception:
                pass

        for part in cleaned.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                cookies_dict[k.strip()] = v.strip()

    cookie_header_str = "; ".join(f"{k}={v}" for k, v in cookies_dict.items())
    return cookie_header_str, cookies_dict


class HLTVScraper:
    def __init__(self):
        self.cookie_header: str = ""
        self.cookies_dict: Dict[str, str] = {}
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: float = 60.0
        self.load_saved_cookie()

    def load_saved_cookie(self):
        """Load cookie from hltv_cookie.txt if present."""
        if os.path.exists(HLTV_COOKIE_FILE):
            try:
                with open(HLTV_COOKIE_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    hdr, c_dict = parse_hltv_cookie_input(content)
                    self.cookie_header = hdr
                    self.cookies_dict = c_dict
                    logger.info(f"HLTV cookie loaded: {len(c_dict)} cookies ({list(c_dict.keys())})")
            except Exception as e:
                logger.error(f"Failed to load HLTV cookie from file: {e}")

    def set_cookie(self, cookie_input: Any) -> tuple[int, List[str]]:
        """Set active cookie and save to hltv_cookie.txt."""
        hdr, c_dict = parse_hltv_cookie_input(cookie_input)
        self.cookie_header = hdr
        self.cookies_dict = c_dict

        try:
            with open(HLTV_COOKIE_FILE, "w", encoding="utf-8") as f:
                if isinstance(cookie_input, (list, dict)):
                    json.dump(cookie_input, f, indent=2, ensure_ascii=False)
                elif hdr:
                    f.write(hdr)
                else:
                    f.write("")
        except Exception as e:
            logger.error(f"Failed to persist HLTV cookie to file: {e}")

        return len(c_dict), list(c_dict.keys())

    def _get_client(self) -> httpx.AsyncClient:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1",
        }
        if self.cookie_header:
            headers["Cookie"] = self.cookie_header

        return httpx.AsyncClient(
            headers=headers,
            cookies=self.cookies_dict if self.cookies_dict else None,
            timeout=18.0,
            follow_redirects=True,
        )

    def parse_hltv_html(self, html: str, target_date: str) -> List[EsportsMatchItem]:
        """Parse HLTV matches page HTML."""
        soup = BeautifulSoup(html, "html.parser")
        matches: List[EsportsMatchItem] = []

        # Find upcoming and live matches
        match_elements = soup.find_all(class_=lambda x: x and ("upcomingMatch" in x or "liveMatch" in x or "match" in x.lower()))

        for m_el in match_elements:
            try:
                # 1. Team names
                team_names = [el.get_text(strip=True) for el in m_el.find_all(class_=lambda x: x and ("matchTeamName" in x or "team" in x.lower())) if el.get_text(strip=True)]
                if len(team_names) < 2:
                    continue

                team1 = team_names[0]
                team2 = team_names[1]

                # 2. Time & Date
                time_el = m_el.find(class_=lambda x: x and "matchTime" in x)
                time_str = time_el.get_text(strip=True) if time_el else "--:--"

                # Timestamp attribute if present
                data_time = m_el.get("data-time") or (time_el.get("data-time") if time_el else None)
                ts = None
                start_iso = None
                if data_time:
                    try:
                        ts = int(int(data_time) / 1000 if len(data_time) > 11 else int(data_time))
                        dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
                        start_iso = dt.isoformat()
                        time_str = dt.strftime("%H:%M")
                    except Exception:
                        pass

                if not start_iso and target_date:
                    start_iso = f"{target_date}T{time_str if ':' in time_str else '12:00'}:00Z"

                # 3. Format (BO1, BO3, BO5)
                meta_el = m_el.find(class_=lambda x: x and "matchMeta" in x)
                format_str = "BO3"
                if meta_el:
                    fmt_text = meta_el.get_text(strip=True).upper()
                    if "BO" in fmt_text:
                        m_fmt = re.search(r"BO\d+", fmt_text)
                        format_str = m_fmt.group(0) if m_fmt else fmt_text
                    elif fmt_text:
                        format_str = fmt_text

                # 4. Tournament
                event_el = m_el.find(class_=lambda x: x and ("matchEvent" in x or "event" in x.lower()))
                tourn_name = event_el.get_text(strip=True) if event_el else "Counter-Strike Tournament"

                # 5. Live status & Score
                is_live = "liveMatch" in m_el.get("class", []) or bool(m_el.find(class_=lambda x: x and "live" in x.lower()))
                status = "live" if is_live else "upcoming"

                # 6. Stream link
                stream_url = None
                stream_platform = None
                streams = []
                link_el = m_el.find("a", href=True)
                match_url = f"{BASE_URL}{link_el['href']}" if link_el and link_el['href'].startswith("/") else (link_el['href'] if link_el else None)

                if is_live or match_url:
                    stream_url = match_url or "https://www.hltv.org/live"
                    stream_platform = "hltv"
                    streams.append({
                        "name": "HLTV Match Center",
                        "platform": "hltv",
                        "url": stream_url
                    })

                # Also add Twitch CS category fallback stream
                streams.append({
                    "name": "Twitch (CS2)",
                    "platform": "twitch",
                    "url": "https://www.twitch.tv/directory/category/counter-strike"
                })

                # Deterministic ID
                slug1 = re.sub(r"[^a-zA-Z0-9]", "", team1).lower()
                slug2 = re.sub(r"[^a-zA-Z0-9]", "", team2).lower()
                match_id = f"hltv_cs_{ts or target_date}_{slug1}_{slug2}"

                matches.append(
                    EsportsMatchItem(
                        id=match_id,
                        discipline="counterstrike",
                        discipline_name="Counter-Strike",
                        discipline_icon="cs",
                        tournament_name=tourn_name,
                        stage=format_str,
                        format=format_str,
                        team1_name=team1,
                        team1_short=team1[:10],
                        team2_name=team2,
                        team2_short=team2[:10],
                        score="-" if not is_live else "LIVE",
                        score1=None,
                        score2=None,
                        is_draw=False,
                        status=status,
                        start_date=start_iso,
                        time=time_str,
                        timestamp=ts,
                        stream_url=stream_url,
                        stream_platform=stream_platform,
                        streams=streams,
                        source="hltv",
                        source_url=match_url or "https://www.hltv.org/matches",
                    )
                )
            except Exception as e:
                logger.debug(f"Error parsing HLTV element: {e}")
                continue

        return matches

    async def get_matches(self, selected_date: Optional[str] = None) -> List[EsportsMatchItem]:
        """Fetch matches from HLTV for a specific date (YYYY-MM-DD)."""
        date_str = selected_date or datetime.date.today().isoformat()
        cache_key = f"hltv_{date_str}"
        now = time.time()

        cached = self._cache.get(cache_key)
        if cached and (now - cached["timestamp"] < self._cache_ttl):
            return cached["matches"]

        url = f"{BASE_URL}/matches?selectedDate={date_str}"

        try:
            async with self._get_client() as client:
                r = await client.get(url)
                if r.status_code == 200:
                    matches = self.parse_hltv_html(r.text, date_str)
                    self._cache[cache_key] = {"matches": matches, "timestamp": now}
                    logger.info(f"HLTV scraped {len(matches)} matches for {date_str}")
                    return matches
                elif r.status_code == 403:
                    logger.warning(f"HLTV Cloudflare challenge encountered on {url}. Cookie required.")
                    return cached["matches"] if cached else []
                else:
                    logger.warning(f"HLTV returned HTTP {r.status_code}")
                    return cached["matches"] if cached else []
        except Exception as e:
            logger.error(f"Error fetching HLTV matches: {e}")
            return cached["matches"] if cached else []

    def merge_with_liquipedia(
        self, liquipedia_cs_matches: List[EsportsMatchItem], hltv_matches: List[EsportsMatchItem]
    ) -> List[EsportsMatchItem]:
        """
        Merge Counter-Strike matches from Liquipedia and HLTV:
        - Avoid duplicates by checking normalized team names and time.
        - Add missing matches from HLTV.
        - Enhance Liquipedia matches with HLTV stream / match page when available.
        """
        if not isinstance(hltv_matches, list) or not hltv_matches:
            return list(liquipedia_cs_matches or [])

        merged = list(liquipedia_cs_matches or [])

        def normalize(name: str) -> str:
            return re.sub(r"[^a-zA-Z0-9]", "", name).lower()

        # Build lookup of existing Liquipedia matches
        existing_keys = set()
        for m in liquipedia_cs_matches:
            t1 = normalize(m.team1_short or m.team1_name)
            t2 = normalize(m.team2_short or m.team2_name)
            pair_key = tuple(sorted([t1, t2]))
            existing_keys.add(pair_key)

        added_count = 0
        for hm in hltv_matches:
            t1 = normalize(hm.team1_short or hm.team1_name)
            t2 = normalize(hm.team2_short or hm.team2_name)
            pair_key = tuple(sorted([t1, t2]))

            if pair_key not in existing_keys:
                # Missing from Liquipedia: add from HLTV!
                merged.append(hm)
                existing_keys.add(pair_key)
                added_count += 1
            else:
                # Already exists in Liquipedia: enrich with HLTV link if Liquipedia has no stream
                for lm in merged:
                    lt1 = normalize(lm.team1_short or lm.team1_name)
                    lt2 = normalize(lm.team2_short or lm.team2_name)
                    if tuple(sorted([lt1, lt2])) == pair_key:
                        if not lm.stream_url and hm.stream_url:
                            lm.stream_url = hm.stream_url
                            lm.stream_platform = hm.stream_platform
                        break

        logger.info(f"Merged CS matches: {len(liquipedia_cs_matches)} Liquipedia + {added_count} new HLTV = {len(merged)} total")
        return merged


hltv_scraper = HLTVScraper()
