import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bs4 import BeautifulSoup
from liquipedia_scraper import LiquipediaScraper, DISCIPLINES
from hltv_scraper import HLTVScraper
from models import EsportsMatchItem, EsportsResponse

def test_liquipedia_html_parsing():
    print("=== TEST 1: Liquipedia HTML Parsing with real match ===")
    sample_path = os.path.join(os.path.dirname(__file__), "real_liquipedia_matches.html")
    if not os.path.exists(sample_path):
        print(f"Sample file {sample_path} not found")
        return False

    with open(sample_path, "r", encoding="utf-8") as f:
        html = f.read()

    scraper = LiquipediaScraper()
    soup = BeautifulSoup(html, "html.parser")
    match_div = soup.find("div", class_="match-info")
    assert match_div is not None, "Could not find match-info div in sample"
    m = scraper._parse_match_div(match_div, "mobilelegends")
    assert m is not None, "Failed to parse match"
    print(f"Match ID: {m.id}")
    print(f"Teams: {m.team1_name} [{m.team1_short}] vs {m.team2_name} [{m.team2_short}]")
    print(f"Scores: score1={m.score1}, score2={m.score2}, raw={m.score}")
    print(f"Draw?: {m.is_draw}")
    print(f"Tournament: {m.tournament_name}")
    print(f"Tournament Logo: {m.tournament_logo}")
    print(f"Streams count: {len(m.streams)}")
    for s in m.streams:
        print(f"  - {s}")

    # Assertions
    assert m.tournament_name is not None and len(m.tournament_name) > 0, "Tournament name must not be empty"
    assert "Cambodia" in m.tournament_name, f"Expected Cambodia in tournament name, got: {m.tournament_name}"
    assert m.team1_name == "PRO Esports", f"Unexpected team1: {m.team1_name}"
    assert m.team2_name == "Galaxy Legends", f"Unexpected team2: {m.team2_name}"
    assert m.team1_short == "PRO", f"Unexpected tag1: {m.team1_short}"
    assert m.team2_short == "GXL", f"Unexpected tag2: {m.team2_short}"
    assert len(m.streams) >= 2, f"Expected at least 2 streams, got {len(m.streams)}"
    assert any(s["platform"] == "youtube" for s in m.streams), "Expected youtube stream"
    assert any(s["platform"] == "facebook" for s in m.streams), "Expected facebook stream"
    print("[PASS] Test 1 Passed!")

def test_draw_detection():
    print("\n=== TEST 2: Draw Detection ===")
    scraper = LiquipediaScraper()

    # Create dummy divs for draw test
    draw_html = """
    <div class="infobox_matches_content">
      <div class="match-info-header">
        <span class="timer-object">12:00</span>
        <div class="match-info-header-scoreholder">
          <span class="match-info-header-scoreholder-score">1</span>
          <span class="match-info-header-scoreholder-score">1</span>
        </div>
      </div>
      <div class="match-info-tournament">
        <span class="match-info-tournament-name"><a href="#"><span>DreamLeague Season 22</span></a></span>
      </div>
      <div class="match-info-body">
        <div class="block-team"><span class="team-template-text"><a href="#" title="Team Spirit">Spirit</a></span></div>
        <div class="block-team"><span class="team-template-text"><a href="#" title="Team Liquid">Liquid</a></span></div>
      </div>
      <div class="match-info-links"></div>
    </div>
    """
    soup = BeautifulSoup(draw_html, "html.parser")
    match = scraper._parse_match_div(soup.div, "dota2")
    assert match is not None
    print(f"Match score: {match.score1} : {match.score2}")
    print(f"Match is_draw: {match.is_draw}")
    assert match.is_draw is True, "1:1 match must be detected as draw"
    assert match.score1 == 1 and match.score2 == 1

    # Non-draw test
    nondraw_html = draw_html.replace(
        '<span class="match-info-header-scoreholder-score">1</span>\n          <span class="match-info-header-scoreholder-score">1</span>',
        '<span class="match-info-header-scoreholder-score">2</span>\n          <span class="match-info-header-scoreholder-score">0</span>'
    )
    soup2 = BeautifulSoup(nondraw_html, "html.parser")
    match2 = scraper._parse_match_div(soup2.div, "dota2")
    assert match2 is not None
    assert match2.is_draw is False, "2:0 match must NOT be detected as draw"
    print("[PASS] Test 2 Passed!")

def test_disciplines_coverage():
    print("\n=== TEST 3: Disciplines Coverage ===")
    print(f"Total defined disciplines in DISCIPLINES dict: {len(DISCIPLINES)}")
    assert len(DISCIPLINES) == 27, f"Expected 27 disciplines, found {len(DISCIPLINES)}"
    print("[PASS] Test 3 Passed!")

def test_favicons():
    print("\n=== TEST 4: Favicons in HTML files ===")
    base_dir = os.path.dirname(os.path.dirname(__file__))
    index_path = os.path.join(base_dir, "static", "index.html")
    esports_path = os.path.join(base_dir, "static", "esports.html")

    with open(index_path, "r", encoding="utf-8") as f:
        idx_content = f.read()
    with open(esports_path, "r", encoding="utf-8") as f:
        esp_content = f.read()

    assert '<link rel="icon"' in idx_content, "index.html missing favicon link"
    assert '<link rel="icon"' in esp_content, "esports.html missing favicon link"
    print("[PASS] Favicon in index.html verified")
    print("[PASS] Favicon in esports.html verified")
    print("[PASS] Test 4 Passed!")

if __name__ == "__main__":
    test_liquipedia_html_parsing()
    test_draw_detection()
    test_disciplines_coverage()
    test_favicons()
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
