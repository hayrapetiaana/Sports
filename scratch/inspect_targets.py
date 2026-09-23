import urllib.request
import ssl
from bs4 import BeautifulSoup
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

def inspect_league_pro():
    url = 'https://tt.league-pro.com/en/tournaments?date_from=2026-09-18&date_to=2026-09-19'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
    soup = BeautifulSoup(html, 'html.parser')
    print("=== LEAGUE PRO ===")
    
    # Check script tags
    import re
    scripts = soup.find_all('script')
    for s in scripts:
        src = s.get('src')
        if src:
            print("Script src:", src)
        else:
            txt = s.text.strip()
            if any(k in txt for k in ['__INITIAL_STATE__', '__NUXT__', 'tournaments', 'window.', 'data']):
                print("Inline script snippet:", txt[:300])
                
    # Also check if there are APIs like /api/v1/...
    print("Checking for api endpoints in html:")
    matches = re.findall(r'/api/[a-zA-Z0-9_\-\./]+', html)
    print("API matches:", set(matches))

    # Also check links or tournament cards
    print("All links:")
    for a in soup.find_all('a'):
        href = a.get('href')
        if href and ('tournament' in href or 'match' in href):
            print("Link:", href, a.text.strip().replace('\n', ' ')[:60])


if __name__ == '__main__':
    inspect_league_pro()
