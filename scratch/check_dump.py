import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'Mozilla/5.0'}

u = 'https://api.sport-liga.pro/tournaments?sport_id=2&limit=5'
req = urllib.request.Request(u, headers=headers)
with urllib.request.urlopen(req, context=ctx) as r:
    data = json.loads(r.read().decode('utf-8', errors='ignore'))

with open('scratch/dump_tourn.json', 'w', encoding='utf-8') as f:
    json.dump(data['items'][0], f, indent=2, ensure_ascii=False)

# Also let's inspect matches endpoint:
u_m = 'https://api.sport-liga.pro/matches?sport_id=2&limit=5'
req_m = urllib.request.Request(u_m, headers=headers)
with urllib.request.urlopen(req_m, context=ctx) as r:
    data_m = json.loads(r.read().decode('utf-8', errors='ignore'))

with open('scratch/dump_match.json', 'w', encoding='utf-8') as f:
    json.dump(data_m['items'][0], f, indent=2, ensure_ascii=False)

print("Dumped successfully to scratch/dump_tourn.json and scratch/dump_match.json")

