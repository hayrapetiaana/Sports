import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'Mozilla/5.0'}

# Check sport-liga tournaments across different days or look at sport-liga.pro web page text
for sid in [1, 2, 4, 5, 6, 9, 10]:
    u = f'https://api.sport-liga.pro/tournaments?sport_id={sid}&limit=10'
    try:
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, context=ctx) as r:
            data = json.loads(r.read().decode('utf-8', errors='ignore'))
            for it in data.get('items', [])[:3]:
                en = it.get('name_en', '')
                ru = it.get('name_ru', '').encode('ascii', 'replace').decode()
                print(f"sport={sid}: EN='{en}' | RU='{ru}'")
    except Exception as e:
        print(f"sport={sid} err:", e)

