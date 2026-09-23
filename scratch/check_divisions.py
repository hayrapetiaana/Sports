import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'Mozilla/5.0'}

# Test candidate endpoints for divisions or venues or cities
urls = [
    'https://api.sport-liga.pro/table-tennis/divisions',
    'https://api.sport-liga.pro/divisions',
    'https://api.sport-liga.pro/api/divisions',
    'https://api.sport-liga.pro/categories?sport_id=2',
    'https://api.sport-liga.pro/leagues?sport_id=2',
    'https://api.sport-liga.pro/arenas',
    'https://api.sport-liga.pro/tournaments/categories',
    'https://api.sport-liga.pro/tournaments?sport_id=2&limit=5',
]

for u in urls:
    try:
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, context=ctx) as r:
            data = json.loads(r.read().decode('utf-8', errors='ignore'))
            print(f"SUCCESS {u}: keys={list(data.keys()) if isinstance(data, dict) else len(data)}")
            if isinstance(data, dict) and 'items' in data:
                print("  Sample item:", data['items'][0] if data['items'] else None)
    except Exception as e:
        print(f"FAIL {u}: {e}")
