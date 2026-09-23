import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'Mozilla/5.0'}

# Check sport-liga.pro tournaments across multiple dates or limits
u = 'https://api.sport-liga.pro/tournaments?sport_id=2&date_from=2026-09-17&date_to=2026-09-19&limit=50'
req = urllib.request.Request(u, headers=headers)
with urllib.request.urlopen(req, context=ctx) as r:
    data = json.loads(r.read())

print("Total tournaments:", len(data.get('items', [])))
for t in data.get('items', []):
    name_ru = t.get('name_ru') or ''
    name_en = t.get('name_en') or ''
    div = t.get('division')
    print(f"ID={t['id']} | RU: {name_ru.encode('ascii', 'replace').decode()} | EN: {name_en} | div: {div}")

# Also check single tournament endpoint
if data.get('items'):
    t_id = data['items'][0]['id']
    try:
        req_single = urllib.request.Request(f'https://api.sport-liga.pro/tournaments/{t_id}', headers=headers)
        with urllib.request.urlopen(req_single, context=ctx) as r:
            single_data = json.loads(r.read())
            print(f"Single tournament details keys: {list(single_data.keys())}")
            for k, v in single_data.items():
                if k != 'sides':
                    print(f"  {k}: {str(v)[:100]}")
    except Exception as e:
        print("Single tourn err:", e)
