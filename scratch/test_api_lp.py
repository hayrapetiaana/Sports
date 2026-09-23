import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://tt.league-pro.com',
    'Referer': 'https://tt.league-pro.com/',
}

test_urls = [
    'https://api.league-pro.com/api/v1/tournaments?date_from=2026-09-18&date_to=2026-09-19',
    'https://api.league-pro.com/tournaments?date_from=2026-09-18&date_to=2026-09-19',
    'https://api.league-pro.com/v1/tournaments?date_from=2026-09-18&date_to=2026-09-19',
    'https://api.league-pro.com/api/tournaments?date_from=2026-09-18&date_to=2026-09-19',
    'https://api.league-pro.com/api/v1/table-tennis/tournaments?date_from=2026-09-18&date_to=2026-09-19',
    'https://api.league-pro.com/en/tournaments?date_from=2026-09-18&date_to=2026-09-19',
]

for url in test_urls:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
            data = resp.read().decode('utf-8', errors='ignore')
            print(f"SUCCESS {url} -> {resp.status} len={len(data)}")
            print("Preview:", data[:200])
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} for {url}")
    except Exception as e:
        print(f"ERR for {url}: {e}")
