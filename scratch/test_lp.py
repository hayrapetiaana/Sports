import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'Mozilla/5.0', 'Origin': 'https://tt.league-pro.com', 'Referer': 'https://tt.league-pro.com/'}

u = 'https://api.league-pro.com/tournaments?date_from=2026-09-18&date_to=2026-09-19&limit=100'
req = urllib.request.Request(u, headers=headers)
with urllib.request.urlopen(req, context=ctx) as r:
    data = json.loads(r.read())
print('Total tournaments:', data['pagination']['total_items'])
print('Returned in batch:', len(data['items']))
for t in data['items'][:5]:
    print("Tourn", t["id"], t["name_en"], "start:", t["start_at"], "status:", t["status"])

# Now let's see how website shows tournament schedule
# The user mentioned: https://tt.league-pro.com/en/tournaments?date_from=2026-09-18&date_to=2026-09-19
# In web page links, it showed: /en/tournaments/36728/310075
# Let's check what 36728/310075 is: 36728 is tournament_id, 310075 is match_id!
# And what about: https://api.league-pro.com/tournaments/{t_id}/calendar or matches?
for param in [
    'tournament_id=36734',
    'tournament_ids[]=36734',
    'tournaments[]=36734',
    'tournament=36734',
    'tournaments=36734',
    'date_from=2026-09-18&date_to=2026-09-19'
]:
    u = f'https://api.league-pro.com/matches?{param}&limit=5'
    req = urllib.request.Request(u, headers=headers)
    with urllib.request.urlopen(req, context=ctx) as r:
        res = json.loads(r.read())
        total = res.get("pagination", {}).get("total_items")
        print(param, "-> total:", total)

