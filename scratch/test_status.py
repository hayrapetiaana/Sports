import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'Mozilla/5.0'}

for name, u in [
    ('League Pro', 'https://api.league-pro.com/matches?date_from=2026-09-16&date_to=2026-09-17&limit=20'),
    ('Sport Liga', 'https://api.sport-liga.pro/matches?sport_id=2&date_from=2026-09-16&date_to=2026-09-17&limit=20')
]:
    req = urllib.request.Request(u, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as r:
        data = json.loads(r.read())
        items = data.get('items', [])
        statuses = set(item['status'] for item in items)
        print(f"{name} statuses found: {statuses}")
        for it in items[:3]:
            p1 = it.get('side_one', {}).get('player', {}) or {}
            p2 = it.get('side_two', {}).get('player', {}) or {}
            res = it.get('results', {}) or {}
            st = it.get('status')
            p1_name = p1.get('short_name_en') or p1.get('surname_en') or 'TBA'
            p2_name = p2.get('short_name_en') or p2.get('surname_en') or 'TBA'
            print(f"  {name} status={st}: {p1_name} vs {p2_name}, score={res.get('score_one')}:{res.get('score_two')}, periods={res.get('period_scores')}")

