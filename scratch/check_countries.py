import urllib.request
import ssl
import json
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'Mozilla/5.0'}

# Let's fetch 100 tournaments from api.sport-liga.pro for sport_id=2
u = 'https://api.sport-liga.pro/tournaments?sport_id=2&date_from=2026-09-10&date_to=2026-09-20&limit=100'
req = urllib.request.Request(u, headers=headers)
with urllib.request.urlopen(req, context=ctx) as r:
    data = json.loads(r.read())

print("Found tournaments:", len(data.get('items', [])))
tournament_names = set()
for t in data.get('items', []):
    tournament_names.add(t.get('name_en', ''))
    tournament_names.add(t.get('name_ru', ''))

for n in sorted(list(tournament_names)):
    print(n.encode('ascii', 'replace').decode())

# Also check if players have country, city, or flag!
print("\nChecking player fields:")
if data.get('items'):
    for t in data['items'][:3]:
        for s in t.get('sides', [])[:2]:
            p = s.get('player') or {}
            print("Player keys:", list(p.keys()), "Sample:", p.get('first_name_en'), p.get('surname_en'))
            # Check player details endpoint
            p_id = p.get('id')
            if p_id:
                try:
                    p_req = urllib.request.Request(f'https://api.sport-liga.pro/players/{p_id}', headers=headers)
                    with urllib.request.urlopen(p_req, context=ctx) as pr:
                        p_data = json.loads(pr.read())
                        print(f"Player {p_id} details:", {k: v for k, v in p_data.items() if k not in ('photo', 'avatar')})
                except Exception as e:
                    print(f"Player {p_id} err:", e)
