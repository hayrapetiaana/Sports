from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class Player(BaseModel):
    id: Optional[int] = None
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[bool] = None
    photo_url: Optional[str] = None
    color_id: Optional[int] = None
    is_serving: bool = False


class SetScore(BaseModel):
    set: int
    p1: Union[int, str] = 0
    p2: Union[int, str] = 0
    is_current: bool = False


class HallInfo(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    official: Optional[int] = None
    stream_url: Optional[str] = None


class PeriodInfo(BaseModel):
    id: int
    name: str


class ScoreSets(BaseModel):
    player1: Union[int, str] = 0
    player2: Union[int, str] = 0
    formatted: str = "0:0"


class MatchItem(BaseModel):
    id: int
    tournament_id: Optional[int] = None
    tournament_name: Optional[str] = None
    time: str  # Formatted local/match time, e.g. "19:45"
    start_date: Optional[str] = None  # Full ISO string
    stage: str  # Tournament name or stage order
    position: Optional[int] = None
    hall: HallInfo
    period: PeriodInfo
    player1: Player
    player2: Player
    score_sets: ScoreSets
    score_points: List[SetScore] = Field(default_factory=list)
    status: str  # "live", "upcoming", "finished"
    raw_status_id: Optional[int] = None
    winner_id: Optional[int] = None
    is_retired: bool = False
    technical_result: Optional[int] = None


class MatchesResponse(BaseModel):
    total: int
    counts: Dict[str, int] = Field(
        default_factory=lambda: {"all": 0, "live": 0, "upcoming": 0, "finished": 0, "just_finished": 0}
    )
    date: str
    halls_filter: Optional[List[int]] = None
    periods_filter: Optional[List[int]] = None
    status_filter: Optional[str] = None
    cached: bool = False
    cache_age_seconds: Optional[float] = None
    matches: List[MatchItem]


# ==============================================================================
# TT Cup (ttcup.com) Models
# ==============================================================================

class TTCupTournament(BaseModel):
    hall_id: int
    name: str
    country: str  # e.g. "Czech Republic", "Poland", "Ukraine", "Unknown"
    country_code: str  # "cz", "pl", "ua", "unknown"
    date: str  # "17.09.2026"
    time: Optional[str] = None  # "20:55"
    period_text: Optional[str] = None  # "17.09.2026 - 18.09.2026"
    url: str  # "/schedule/17.09.2026/h:9/"
    full_url: str  # "https://ttcup.com/schedule/17.09.2026/h:9/"


class TTCupMatch(BaseModel):
    order: Optional[int] = None
    time: str  # "20:55"
    date: str  # "17.09.2026"
    timezone: str = "CET"
    hall_id: int
    tournament_name: str
    country: str
    stage: str = "Group Stage"  # "Group Stage", "Final games", etc.
    player1_name: str
    player1_url: Optional[str] = None
    player2_name: str
    player2_url: Optional[str] = None
    score: str = "-"  # "3:1", "-", "0:0"
    set_scores: Optional[str] = None  # "11:8, 9:11, 11:7" or "-"
    status: str = "upcoming"  # "upcoming", "live", "finished"
    start_date: Optional[str] = None  # Full ISO string e.g. "2026-09-17T20:55:00+02:00"
    vs_url: Optional[str] = None


class TTCupStandingsRow(BaseModel):
    pos: int
    player_name: str
    scores: List[str] = Field(default_factory=list)
    points: int = 0


class TTCupScheduleDetail(BaseModel):
    tournament: TTCupTournament
    matches: List[TTCupMatch] = Field(default_factory=list)
    standings: List[TTCupStandingsRow] = Field(default_factory=list)
    cached: bool = False


class TTCupMatchesResponse(BaseModel):
    total: int
    counts: Dict[str, int] = Field(
        default_factory=lambda: {"all": 0, "live": 0, "upcoming": 0, "finished": 0, "just_finished": 0}
    )
    date: str
    country_filter: Optional[str] = None
    halls_filter: Optional[List[int]] = None
    from_time: Optional[str] = None
    to_time: Optional[str] = None
    status_filter: Optional[str] = None
    search: Optional[str] = None
    cached: bool = False
    cache_age_seconds: Optional[float] = None
    captcha_required: bool = False
    available_tournaments: List[TTCupTournament] = Field(default_factory=list)
    matches: List[TTCupMatch] = Field(default_factory=list)


class TTCupConfigUpdate(BaseModel):
    cookie: Optional[Any] = None
    proxy: Optional[str] = None


# ==============================================================================
# League Pro (tt.league-pro.com) Models
# ==============================================================================

class LeagueProPlayer(BaseModel):
    id: Optional[int] = None
    name: str
    short_name: Optional[str] = None
    avatar: Optional[str] = None
    rating: Optional[float] = None


class LeagueProTournament(BaseModel):
    id: int
    name: str
    start_at: str  # ISO 8601 string
    status: int  # 1 = scheduled, 2 = live, 3 = finished
    sides_count: Optional[int] = None
    players: List[LeagueProPlayer] = Field(default_factory=list)


class LeagueProMatch(BaseModel):
    id: int
    tournament_id: int
    tournament_name: str
    stage: str
    start_date: str  # ISO 8601 string UTC
    time: str  # Formatted HH:MM
    player1: LeagueProPlayer
    player2: LeagueProPlayer
    score: str  # e.g. "3:1" or "-"
    set_scores: Optional[str] = None  # e.g. "11:8, 9:11, 11:7"
    status: str  # "live", "upcoming", "finished"
    raw_status: int


class LeagueProMatchesResponse(BaseModel):
    total: int
    counts: Dict[str, int] = Field(
        default_factory=lambda: {"all": 0, "live": 0, "upcoming": 0, "finished": 0, "just_finished": 0}
    )
    date_from: str
    date_to: str
    tournament_filter: Optional[int] = None
    status_filter: Optional[str] = None
    from_time: Optional[str] = None
    to_time: Optional[str] = None
    search: Optional[str] = None
    cached: bool = False
    cache_age_seconds: Optional[float] = None
    tournaments: List[LeagueProTournament] = Field(default_factory=list)
    matches: List[LeagueProMatch] = Field(default_factory=list)


# ==============================================================================
# Sport-Liga Pro (sport-liga.pro) Models
# ==============================================================================

class SportLigaTournament(BaseModel):
    id: int
    name: str
    start_at: str  # ISO 8601 string
    status: int
    country: str = "Russia"
    country_code: str = "ru"
    city: Optional[str] = "Moscow"
    sides_count: Optional[int] = None
    players: List[LeagueProPlayer] = Field(default_factory=list)


class SportLigaMatch(BaseModel):
    id: int
    tournament_id: int
    tournament_name: str
    stage: str
    start_date: str  # ISO 8601 string UTC
    time: str  # Formatted HH:MM
    country: str = "Russia"
    country_code: str = "ru"
    city: Optional[str] = "Moscow"
    player1: LeagueProPlayer
    player2: LeagueProPlayer
    score: str  # e.g. "3:1" or "-"
    set_scores: Optional[str] = None
    status: str  # "live", "upcoming", "finished"
    raw_status: int


class SportLigaMatchesResponse(BaseModel):
    total: int
    counts: Dict[str, int] = Field(
        default_factory=lambda: {"all": 0, "live": 0, "upcoming": 0, "finished": 0, "just_finished": 0}
    )
    date_from: str
    date_to: str
    tournament_filter: Optional[int] = None
    status_filter: Optional[str] = None
    from_time: Optional[str] = None
    to_time: Optional[str] = None
    search: Optional[str] = None
    cached: bool = False
    cache_age_seconds: Optional[float] = None
    tournaments: List[SportLigaTournament] = Field(default_factory=list)
    matches: List[SportLigaMatch] = Field(default_factory=list)


# ==============================================================================
# Unified Cross-Platform Models
# ==============================================================================

class UnifiedMatchItem(BaseModel):
    id: str  # e.g. "setka_12345", "ttcup_9_12", "leaguepro_310258", "ligapro_77758"
    platform: str  # "setka", "ttcup", "league_pro", "sport_liga"
    platform_name: str  # "Setka Cup", "TT Cup", "League Pro", "Liga Pro"
    tournament_id: Optional[str] = None
    tournament_name: str
    stage: Optional[str] = None
    start_date: Optional[str] = None  # Normalized ISO 8601 timestamp with offset or Z
    time: str  # HH:MM string
    country: Optional[str] = None
    country_code: Optional[str] = None  # "cz", "pl", "ua", "ru", "by", "md"
    city: Optional[str] = None  # "Moscow", "Minsk", "Chisinau", "Prague", etc.
    player1_name: str
    player1_photo: Optional[str] = None
    player2_name: str
    player2_photo: Optional[str] = None
    score: str = "-"
    set_scores: Optional[str] = None
    status: str = "upcoming"  # "live", "upcoming", "finished"
    url: Optional[str] = None


class UnifiedMatchesResponse(BaseModel):
    total: int
    counts: Dict[str, int] = Field(
        default_factory=lambda: {"all": 0, "live": 0, "upcoming": 0, "finished": 0, "just_finished": 0}
    )
    platform_counts: Dict[str, int] = Field(
        default_factory=lambda: {"setka": 0, "ttcup": 0, "league_pro": 0, "sport_liga": 0, "liga_pro": 0}
    )
    date_from: str
    date_to: str

    from_time: Optional[str] = None
    to_time: Optional[str] = None
    status_filter: Optional[str] = None
    platform_filter: Optional[str] = None
    search: Optional[str] = None
    matches: List[UnifiedMatchItem] = Field(default_factory=list)


# ==============================================================================
# Removed Matches Models
# ==============================================================================

class RemovedMatchItem(BaseModel):
    id: str
    platform: str
    platform_name: str
    tournament_name: str
    stage: Optional[str] = None
    start_date: Optional[str] = None
    time: str
    country: Optional[str] = None
    country_code: Optional[str] = None
    player1_name: str
    player1_photo: Optional[str] = None
    player2_name: str
    player2_photo: Optional[str] = None
    score: str = "-"
    set_scores: Optional[str] = None
    status: str = "upcoming"
    url: Optional[str] = None
    first_seen_at: float  # Unix timestamp
    last_seen_at: float   # Unix timestamp
    removed_at: float     # Unix timestamp
    removed_reason: str   # Reason for removal (e.g. "Не поступало обновлений более 5 минут")


class RemovedMatchesResponse(BaseModel):
    total: int
    matches: List[RemovedMatchItem] = Field(default_factory=list)


# ==============================================================================
# Esports (Liquipedia + HLTV) Models
# ==============================================================================

class EsportsMatchItem(BaseModel):
    id: str
    discipline: str              # e.g. "dota2", "counterstrike", "valorant"
    discipline_name: str         # e.g. "Dota 2", "Counter-Strike", "VALORANT"
    discipline_icon: Optional[str] = None
    tournament_name: str
    tournament_logo: Optional[str] = None
    stage: Optional[str] = None
    format: Optional[str] = "BO3"  # BO1, BO2, BO3, BO5, BO7
    team1_name: str
    team1_short: Optional[str] = None
    team1_logo: Optional[str] = None
    team2_name: str
    team2_short: Optional[str] = None
    team2_logo: Optional[str] = None
    score: str = "-"
    score1: Optional[Union[int, str]] = None
    score2: Optional[Union[int, str]] = None
    is_draw: bool = False
    status: str = "upcoming"     # live, upcoming, finished, draw
    start_date: Optional[str] = None  # ISO format: 2026-09-18T14:00:00Z
    time: str = "--:--"
    timestamp: Optional[int] = None
    stream_url: Optional[str] = None
    stream_platform: Optional[str] = None  # "twitch", "youtube", "kick", "hltv"
    streams: List[Dict[str, str]] = Field(default_factory=list)
    source: str = "liquipedia"   # "liquipedia", "hltv", "liquipedia+hltv"
    source_url: Optional[str] = None
    details: Optional[str] = None


class EsportsResponse(BaseModel):
    total: int
    counts: Dict[str, int] = Field(
        default_factory=lambda: {"all": 0, "live": 0, "upcoming": 0, "finished": 0, "draw": 0}
    )
    discipline_counts: Dict[str, int] = Field(default_factory=dict)
    discipline_filter: Optional[str] = "all"
    status_filter: Optional[str] = "all"
    date_filter: Optional[str] = None
    search: Optional[str] = None
    matches: List[EsportsMatchItem] = Field(default_factory=list)


class EsportsRemovedMatchItem(BaseModel):
    id: str
    discipline: str
    discipline_name: str
    tournament_name: str
    tournament_logo: Optional[str] = None
    stage: Optional[str] = None
    format: Optional[str] = "BO3"
    team1_name: str
    team1_short: Optional[str] = None
    team2_name: str
    team2_short: Optional[str] = None
    score: str = "-"
    score1: Optional[Union[int, str]] = None
    score2: Optional[Union[int, str]] = None
    is_draw: bool = False
    status: str = "upcoming"
    start_date: Optional[str] = None
    time: str = "--:--"
    stream_url: Optional[str] = None
    stream_platform: Optional[str] = None
    streams: List[Dict[str, str]] = Field(default_factory=list)
    source: str = "liquipedia"
    source_url: Optional[str] = None
    first_seen_at: float
    last_seen_at: float
    removed_at: float
    removed_reason: str


class EsportsRemovedMatchesResponse(BaseModel):
    total: int
    matches: List[EsportsRemovedMatchItem] = Field(default_factory=list)


class HLTVConfigUpdate(BaseModel):
    cookie: Optional[Any] = None
    raw_cookie: Optional[Any] = None


class LiquipediaConfigUpdate(BaseModel):
    cookie: Optional[Any] = None
    raw_cookie: Optional[Any] = None



