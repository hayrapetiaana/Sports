import httpx

def test_sources():
    # 1. Test Liquipedia API
    lp_api = "https://liquipedia.net/dota2/api.php?action=parse&page=Liquipedia:Matches&format=json"
    headers_lp = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html, */*"
    }
    with httpx.Client(headers=headers_lp, follow_redirects=True, timeout=10) as client:
        r = client.get(lp_api)
        print("Liquipedia API status:", r.status_code)
        if r.status_code == 200:
            print("Liquipedia API keys:", list(r.json().keys()))

    # 2. Test HLTV
    hltv_url = "https://www.hltv.org/matches"
    headers_hltv = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }
    with httpx.Client(headers=headers_hltv, follow_redirects=True, timeout=10) as client:
        r = client.get(hltv_url)
        print("HLTV status:", r.status_code)
        print("HLTV text len:", len(r.text))
        if "upcomingMatchesSection" in r.text or "liveMatch" in r.text or "match-day" in r.text:
            print("HLTV matches found in HTML!")

if __name__ == "__main__":
    test_sources()
