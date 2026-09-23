"""
Liquipedia Scraper module.
Fetches esports matches for 25+ disciplines using the official Liquipedia MediaWiki API:
https://liquipedia.net/{discipline}/api.php?action=parse&page=Liquipedia:Matches&format=json
Extracts:
- Team full names and short initials/tags
- Team logos (dark and light mode)
- Match formats (BO1, BO2, BO3, BO5, BO7)
- Live stream translations (Twitch, YouTube, Kick)
- Tournament names and logos
- Scores and live/upcoming/finished statuses
"""

import asyncio
import datetime
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import httpx

from models import EsportsMatchItem

logger = logging.getLogger("liquipedia_scraper")
logging.basicConfig(level=logging.INFO)

DISCIPLINES: Dict[str, Dict[str, str]] = {
    "dota2": {"name": "Dota 2", "icon": "dota2", "color": "#E74C3C", "twitch_game": "Dota 2"},
    "counterstrike": {"name": "Counter-Strike", "icon": "cs", "color": "#E67E22", "twitch_game": "Counter-Strike"},
    "valorant": {"name": "VALORANT", "icon": "valorant", "color": "#FD4556", "twitch_game": "VALORANT"},
    "mobilelegends": {"name": "Mobile Legends", "icon": "mlbb", "color": "#3498DB", "twitch_game": "Mobile Legends: Bang Bang"},
    "rocketleague": {"name": "Rocket League", "icon": "rl", "color": "#0088FF", "twitch_game": "Rocket League"},
    "leagueoflegends": {"name": "League of Legends", "icon": "lol", "color": "#C8AA6E", "twitch_game": "League of Legends"},
    "overwatch": {"name": "Overwatch", "icon": "ow", "color": "#FA9C1E", "twitch_game": "Overwatch 2"},
    "rainbowsix": {"name": "Rainbow Six", "icon": "r6", "color": "#2C3E50", "twitch_game": "Tom Clancy's Rainbow Six Siege"},
    "pubgmobile": {"name": "PUBG Mobile", "icon": "pubgm", "color": "#F39C12", "twitch_game": "PUBG Mobile"},
    "apexlegends": {"name": "Apex Legends", "icon": "apex", "color": "#DA292A", "twitch_game": "Apex Legends"},
    "fighters": {"name": "Fighting Games", "icon": "fgc", "color": "#E74C3C", "twitch_game": "Street Fighter 6"},
    "ageofempires": {"name": "Age of Empires", "icon": "aoe", "color": "#2980B9", "twitch_game": "Age of Empires IV"},
    "pubg": {"name": "PUBG", "icon": "pubg", "color": "#F1C40F", "twitch_game": "PUBG: BATTLEGROUNDS"},
    "starcraft2": {"name": "StarCraft II", "icon": "sc2", "color": "#3498DB", "twitch_game": "StarCraft II"},
    "brawlstars": {"name": "Brawl Stars", "icon": "brawl", "color": "#9B59B6", "twitch_game": "Brawl Stars"},
    "honorofkings": {"name": "Honor of Kings", "icon": "hok", "color": "#1ABC9C", "twitch_game": "Honor of Kings"},
    "callofduty": {"name": "Call of Duty", "icon": "cod", "color": "#34495E", "twitch_game": "Call of Duty: Warzone"},
    "marvelrivals": {"name": "Marvel Rivals", "icon": "mr", "color": "#E74C3C", "twitch_game": "Marvel Rivals"},
    "fortnite": {"name": "Fortnite", "icon": "fn", "color": "#9B59B6", "twitch_game": "Fortnite"},
    "warcraft": {"name": "Warcraft", "icon": "wc3", "color": "#D35400", "twitch_game": "Warcraft III: The Frozen Throne"},
    "smash": {"name": "Smash", "icon": "smash", "color": "#E74C3C", "twitch_game": "Super Smash Bros. Ultimate"},
    "starcraft": {"name": "StarCraft", "icon": "sc", "color": "#2980B9", "twitch_game": "StarCraft: Remastered"},
    "worldoftanks": {"name": "World of Tanks", "icon": "wot", "color": "#C0392B", "twitch_game": "World of Tanks"},
    "easportsfc": {"name": "EA SPORTS FC", "icon": "fc", "color": "#27AE60", "twitch_game": "EA SPORTS FC 25"},
    "hearthstone": {"name": "Hearthstone", "icon": "hs", "color": "#F39C12", "twitch_game": "Hearthstone"},
    "heroes": {"name": "Heroes of the Storm", "icon": "hots", "color": "#8E44AD", "twitch_game": "Heroes of the Storm"},
    "wildrift": {"name": "Wild Rift", "icon": "wr", "color": "#1ABC9C", "twitch_game": "League of Legends: Wild Rift"},
}

BASE_URL = "https://liquipedia.net"


COOKIE_FILE_PATH = os.path.join(os.path.dirname(__file__), "liquipedia_cookie.txt")


def parse_liquipedia_cookie_input(raw_input: Any) -> tuple[str, Dict[str, str]]:
    cookies_dict = {}
    if not raw_input:
        return "", {}

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
                import json
                parsed_json = json.loads(cleaned)
                return parse_liquipedia_cookie_input(parsed_json)
            except Exception:
                pass

        for part in cleaned.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                cookies_dict[k.strip()] = v.strip()

    cookie_header_str = "; ".join(f"{k}={v}" for k, v in cookies_dict.items())
    return cookie_header_str, cookies_dict


class LiquipediaScraper:
    def __init__(self):
        self.cookie_header: str = ""
        self.cookies_dict: Dict[str, str] = {}
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: float = 60.0  # 60 seconds cache per game
        self.headers = {
            "User-Agent": "EsportsMatchesParser/1.0 (https://github.com/hayran; support@esportsparser.local) Mozilla/5.0",
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        }
        self.load_saved_cookie()

    def load_saved_cookie(self):
        if os.path.exists(COOKIE_FILE_PATH):
            try:
                with open(COOKIE_FILE_PATH, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    self.cookie_header, self.cookies_dict = parse_liquipedia_cookie_input(content)
                    logger.info(f"Loaded {len(self.cookies_dict)} Liquipedia cookies from {COOKIE_FILE_PATH}")
            except Exception as e:
                logger.warning(f"Failed to load saved Liquipedia cookie: {e}")

    def set_cookie(self, cookie_input: Any) -> tuple[int, List[str]]:
        self.cookie_header, self.cookies_dict = parse_liquipedia_cookie_input(cookie_input)
        try:
            with open(COOKIE_FILE_PATH, "w", encoding="utf-8") as f:
                if isinstance(cookie_input, (list, dict)):
                    import json
                    f.write(json.dumps(cookie_input, indent=2))
                else:
                    f.write(str(cookie_input or ""))
            logger.info(f"Saved Liquipedia cookie to {COOKIE_FILE_PATH}")
        except Exception as e:
            logger.error(f"Failed to save Liquipedia cookie to file: {e}")
        return len(self.cookies_dict), list(self.cookies_dict.keys())

    def _get_client(self) -> httpx.AsyncClient:
        headers = dict(self.headers)
        if self.cookie_header:
            headers["Cookie"] = self.cookie_header
        return httpx.AsyncClient(
            headers=headers,
            cookies=self.cookies_dict if self.cookies_dict else None,
            timeout=18.0,
            follow_redirects=True,
        )

    def _fix_url(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return BASE_URL + url
        return url

    def _clean_text(self, text: Optional[str]) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def _parse_stream_links(self, div: BeautifulSoup, discipline: str, team1: str, team2: str) -> tuple[List[Dict[str, str]], Optional[str], Optional[str]]:
        """Extract all stream links and determine primary stream URL/platform."""
        streams: List[Dict[str, str]] = []
        seen_urls = set()

        def add_stream(name: str, platform: str, url: str):
            if not url or url in seen_urls:
                return
            seen_urls.add(url)
            streams.append({"name": name, "platform": platform, "url": url})

        # 1. Search in links container and anywhere inside match div
        for a in div.find_all("a", href=True):
            href = a["href"]
            title = a.get("title", "")
            lower_href = href.lower()

            if "special:stream/youtube/" in lower_href:
                channel = href.split("special:stream/youtube/")[-1].split("Special:Stream/youtube/")[-1].split("?")[0].strip("/")
                ch_clean = channel.replace("_", " ")
                add_stream(f"YouTube ({ch_clean})", "youtube", f"https://youtube.com/@{channel}")
            elif "special:stream/twitch/" in lower_href:
                channel = href.split("special:stream/twitch/")[-1].split("Special:Stream/twitch/")[-1].split("?")[0].strip("/")
                ch_clean = channel.replace("_", " ")
                add_stream(f"Twitch ({ch_clean})", "twitch", f"https://twitch.tv/{channel}")
            elif "special:stream/facebook/" in lower_href:
                channel = href.split("special:stream/facebook/")[-1].split("Special:Stream/facebook/")[-1].split("?")[0].strip("/")
                ch_clean = channel.replace("_", " ")
                add_stream(f"Facebook ({ch_clean})", "facebook", f"https://facebook.com/{channel}")
            elif "special:stream/kick/" in lower_href:
                channel = href.split("special:stream/kick/")[-1].split("Special:Stream/kick/")[-1].split("?")[0].strip("/")
                ch_clean = channel.replace("_", " ")
                add_stream(f"Kick ({ch_clean})", "kick", f"https://kick.com/{channel}")
            elif "special:stream/afreecatv/" in lower_href:
                channel = href.split("special:stream/afreecatv/")[-1].split("Special:Stream/afreecatv/")[-1].split("?")[0].strip("/")
                add_stream(f"AfreecaTV ({channel})", "afreecatv", f"https://play.afreecatv.com/{channel}")
            elif "special:stream/bilibili/" in lower_href:
                channel = href.split("special:stream/bilibili/")[-1].split("Special:Stream/bilibili/")[-1].split("?")[0].strip("/")
                add_stream(f"Bilibili ({channel})", "bilibili", f"https://live.bilibili.com/{channel}")
            elif "twitch.tv/" in lower_href and not lower_href.endswith("/twitch.tv/"):
                full_url = href if href.startswith("http") else f"https:{href}"
                add_stream("Twitch", "twitch", full_url)
            elif "youtube.com/" in lower_href or "youtu.be/" in lower_href:
                full_url = href if href.startswith("http") else f"https:{href}"
                add_stream("YouTube", "youtube", full_url)
            elif "kick.com/" in lower_href:
                full_url = href if href.startswith("http") else f"https:{href}"
                add_stream("Kick", "kick", full_url)

        # 2. If no streams found, add fallback discipline broadcast directory
        if not streams:
            twitch_game = DISCIPLINES.get(discipline, {}).get("twitch_game")
            d_name = DISCIPLINES.get(discipline, {}).get("name", discipline)
            if twitch_game:
                encoded = twitch_game.replace(" ", "%20")
                streams.append({
                    "name": f"Twitch ({d_name})",
                    "platform": "twitch",
                    "url": f"https://www.twitch.tv/directory/category/{encoded}",
                })
            else:
                streams.append({
                    "name": f"Twitch ({d_name})",
                    "platform": "twitch",
                    "url": f"https://www.twitch.tv/search?term={discipline}",
                })

        primary_url = streams[0]["url"] if streams else None
        primary_platform = streams[0]["platform"] if streams else None
        return streams, primary_url, primary_platform

    def _parse_match_div(self, div: BeautifulSoup, discipline: str) -> Optional[EsportsMatchItem]:
        try:
            # 1. Timestamp & Time
            timer_span = div.find(class_="timer-object")
            timestamp = None
            start_date_iso = None
            time_str = "--:--"
            if timer_span and timer_span.get("data-timestamp"):
                try:
                    ts = int(timer_span["data-timestamp"])
                    timestamp = ts
                    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
                    start_date_iso = dt.isoformat()
                    time_str = dt.strftime("%H:%M")
                except (ValueError, TypeError):
                    pass

            now_ts = int(time.time())

            # 2. Opponents (Team 1 & Team 2)
            opponents = div.find_all(class_=lambda c: c and ("opponent" in c or "block-team" in c))
            # Filter distinct opponents
            valid_opponents = []
            for o in opponents:
                if any(cls in o.get("class", []) for cls in ["match-info-header-opponent", "opponent-left", "opponent-right"]):
                    valid_opponents.append(o)

            if len(valid_opponents) < 2:
                # Try finding opponent-left and opponent-right
                opp1 = div.find(class_=lambda x: x and "opponent-left" in x)
                opp2 = div.find(class_=lambda x: x and "opponent-right" in x)
                if opp1 and opp2:
                    valid_opponents = [opp1, opp2]
                else:
                    # Fallback to general block-team
                    blocks = div.find_all(class_="block-team")
                    if len(blocks) >= 2:
                        valid_opponents = [blocks[0], blocks[1]]
                    else:
                        return None

            def extract_team(opp_el) -> tuple[str, str, Optional[str]]:
                full_name = ""
                short_name = ""
                logo_url = None

                # Search anchor for title
                a_tags = opp_el.find_all("a", title=True)
                for a in a_tags:
                    t = self._clean_text(a.get("title", ""))
                    if t and not full_name:
                        full_name = t

                # Search name element
                name_span = opp_el.find(class_=lambda c: c and ("name" in c or "team-template-text" in c))
                if name_span:
                    short_name = self._clean_text(name_span.get_text())

                if not full_name:
                    full_name = short_name or "TBD"
                if not short_name:
                    short_name = full_name

                # Image logo
                img = opp_el.find("img")
                if img:
                    logo_url = self._fix_url(img.get("src"))

                return full_name, short_name, logo_url

            team1_name, team1_short, team1_logo = extract_team(valid_opponents[0])
            team2_name, team2_short, team2_logo = extract_team(valid_opponents[1])

            # 3. Format and Score
            scoreholder = div.find(class_=lambda c: c and "scoreholder" in c)
            format_str = "BO3"
            score_str = "-"
            score1: Optional[Union[int, str]] = None
            score2: Optional[Union[int, str]] = None
            is_draw = False
            status = "upcoming"

            if scoreholder:
                # Best-of Format
                lower = scoreholder.find(class_=lambda c: c and "lower" in c)
                if lower:
                    lower_txt = lower.get_text()
                    fmt_match = re.search(r"bo\s*(\d+)", lower_txt, re.IGNORECASE)
                    if fmt_match:
                        format_str = f"BO{fmt_match.group(1)}"
                    else:
                        fmt_clean = self._clean_text(lower_txt).strip("()")
                        if fmt_clean:
                            format_str = fmt_clean.upper()

                # Extract score spans
                score_spans = scoreholder.find_all(class_=lambda c: c and "scoreholder-score" in c)
                if len(score_spans) >= 2:
                    try:
                        s1 = int(self._clean_text(score_spans[0].get_text()))
                        s2 = int(self._clean_text(score_spans[1].get_text()))
                        score1, score2 = s1, s2
                        score_str = f"{s1}:{s2}"
                    except Exception:
                        pass

                if score1 is None:
                    upper = scoreholder.find(class_=lambda c: c and "upper" in c)
                    raw_score = self._clean_text(upper.get_text()) if upper else ""
                    if raw_score and raw_score.lower() != "vs":
                        sm = re.search(r"(\d+)\s*[:\-]\s*(\d+)", raw_score)
                        if sm:
                            score1 = int(sm.group(1))
                            score2 = int(sm.group(2))
                            score_str = f"{score1}:{score2}"
                        elif "draw" in raw_score.lower() or "tie" in raw_score.lower():
                            is_draw = True
                            score_str = "Draw"

            # 4. Status deduction
            has_winner = bool(div.find(class_=lambda c: c and ("winner" in c or "match-info-header-winner" in c)))
            has_loser = bool(div.find(class_=lambda c: c and ("loser" in c or "match-info-header-loser" in c)))

            if has_winner or has_loser:
                status = "finished"
            elif timestamp:
                diff = now_ts - timestamp
                if diff < -300:
                    status = "upcoming"
                elif -300 <= diff <= 7200:
                    if score1 is not None and score2 is not None and (score1 > 0 or score2 > 0):
                        status = "live"
                    elif diff > 300:
                        status = "live"
                    else:
                        status = "upcoming"
                elif diff > 7200:
                    status = "finished" if score_str != "-" else "upcoming"
            else:
                status = "finished" if score_str != "-" else "upcoming"

            # 5. Draw detection (e.g. BO2 1:1, or equal score with finished/draw status)
            if score1 is not None and score2 is not None and score1 == score2:
                if status == "finished" or format_str in ["BO2", "2"]:
                    is_draw = True
                elif score1 > 0 and not has_winner and not has_loser:
                    is_draw = True
            elif "draw" in (score_str or "").lower():
                is_draw = True

            # 6. Tournament & Stage extraction
            tourn_name = "Tournament"
            tourn_logo = None
            stage_str = ""

            tourn_div = div.find(class_=lambda c: c and "tournament" in c)
            if tourn_div:
                name_el = tourn_div.find(class_=lambda c: c and "tournament-name" in c)
                if name_el:
                    tourn_name = self._clean_text(name_el.get_text())

                if not tourn_name or tourn_name.lower() == "tournament":
                    # Search inside anchor tags
                    for a in tourn_div.find_all("a"):
                        t_title = self._clean_text(a.get("title", ""))
                        t_text = self._clean_text(a.get_text())
                        candidate = t_title or t_text
                        if candidate and candidate.lower() not in ["tournament", ""]:
                            tourn_name = candidate
                            break

                img = tourn_div.find("img")
                if img:
                    tourn_logo = self._fix_url(img.get("src"))

            # Fallback for tournament name
            if not tourn_name or tourn_name.lower() == "tournament":
                d_meta = DISCIPLINES.get(discipline, {})
                tourn_name = f"{d_meta.get('name', discipline.capitalize())} Event"

            # 7. Streams extraction
            streams, stream_url, stream_platform = self._parse_stream_links(div, discipline, team1_name, team2_name)

            # Unique deterministic ID
            slug1 = re.sub(r"[^a-zA-Z0-9]", "", team1_short or team1_name).lower()
            slug2 = re.sub(r"[^a-zA-Z0-9]", "", team2_short or team2_name).lower()
            match_id = f"lp_{discipline}_{timestamp or '0'}_{slug1}_{slug2}"

            disc_meta = DISCIPLINES.get(discipline, {})

            return EsportsMatchItem(
                id=match_id,
                discipline=discipline,
                discipline_name=disc_meta.get("name", discipline.capitalize()),
                discipline_icon=disc_meta.get("icon"),
                tournament_name=tourn_name,
                tournament_logo=tourn_logo,
                stage=stage_str or format_str,
                format=format_str,
                team1_name=team1_name,
                team1_short=team1_short,
                team1_logo=team1_logo,
                team2_name=team2_name,
                team2_short=team2_short,
                team2_logo=team2_logo,
                score=score_str,
                score1=score1,
                score2=score2,
                is_draw=is_draw,
                status=status,
                start_date=start_date_iso,
                time=time_str,
                timestamp=timestamp,
                stream_url=stream_url,
                stream_platform=stream_platform,
                streams=streams,
                source="liquipedia",
                source_url=f"https://liquipedia.net/{discipline}/Liquipedia:Matches",
            )
        except Exception as e:
            logger.debug(f"Error parsing match div: {e}")
            return None

    async def get_discipline_matches(self, discipline: str) -> List[EsportsMatchItem]:
        """Fetch matches for a single discipline from Liquipedia MediaWiki API."""
        now = time.time()
        cached = self._cache.get(discipline)
        if cached and (now - cached["timestamp"] < self._cache_ttl):
            return cached["matches"]

        api_url = f"https://liquipedia.net/{discipline}/api.php?action=parse&page=Liquipedia:Matches&format=json"

        try:
            async with self._get_client() as client:
                r = await client.get(api_url)
                if r.status_code != 200:
                    logger.warning(f"Liquipedia API returned {r.status_code} for {discipline}")
                    return cached["matches"] if cached else []

                data = r.json()
                html = data.get("parse", {}).get("text", {}).get("*", "")
                if not html:
                    return cached["matches"] if cached else []

                soup = BeautifulSoup(html, "html.parser")
                match_divs = soup.find_all(class_=lambda c: c and ("match-info" in c or "matches-list" in c))
                if not match_divs:
                    match_divs = soup.find_all(class_="match-info")

                matches: List[EsportsMatchItem] = []
                for m_div in match_divs:
                    item = self._parse_match_div(m_div, discipline)
                    if item:
                        matches.append(item)

                self._cache[discipline] = {
                    "matches": matches,
                    "timestamp": now,
                }
                logger.info(f"Loaded {len(matches)} matches for {discipline}")
                return matches
        except Exception as e:
            logger.error(f"Failed to fetch matches for {discipline}: {e}")
            return cached["matches"] if cached else []

    async def get_all_matches(self, disciplines: Optional[List[str]] = None) -> List[EsportsMatchItem]:
        """Fetch matches across multiple disciplines with concurrency control."""
        target_disciplines = disciplines or list(DISCIPLINES.keys())
        sem = asyncio.Semaphore(5)

        async def fetch_with_sem(d: str):
            async with sem:
                await asyncio.sleep(0.05)
                return await self.get_discipline_matches(d)

        tasks = [fetch_with_sem(d) for d in target_disciplines]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_matches: List[EsportsMatchItem] = []
        for res in results:
            if isinstance(res, list):
                all_matches.extend(res)

        def sort_key(m: EsportsMatchItem):
            st_order = 0 if m.status == "live" else (1 if m.status == "upcoming" else 2)
            ts = m.timestamp or 9999999999
            return (st_order, ts)

        all_matches.sort(key=sort_key)
        return all_matches

    async def scrape_matches(self, discipline: str) -> List[EsportsMatchItem]:
        """Convenience alias for get_discipline_matches."""
        return await self.get_discipline_matches(discipline)


liquipedia_scraper = LiquipediaScraper()
