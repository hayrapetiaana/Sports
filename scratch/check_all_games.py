import httpx
import json

games = [
    "dota2", "counterstrike", "valorant", "mobilelegends", "rocketleague",
    "leagueoflegends", "overwatch", "rainbowsix", "pubgmobile", "apexlegends",
    "fighters", "ageofempires", "pubg", "starcraft2", "brawlstars",
    "honorofkings", "callofduty", "marvelrivals", "fortnite", "warcraft",
    "smash", "starcraft", "worldoftanks", "easportsfc", "hearthstone",
    "heroes", "wildrift"
]

results = {}
headers = {"User-Agent": "Mozilla/5.0"}

with httpx.Client(headers=headers, timeout=10) as client:
    for g in games:
        api = f"https://liquipedia.net/{g}/api.php?action=parse&page=Liquipedia:Matches&format=json"
        try:
            r = client.get(api)
            if r.status_code == 200:
                html = r.json().get("parse", {}).get("text", {}).get("*", "")
                has_matches = "match-info" in html or "infobox_matches" in html or "panel-box" in html
                results[g] = {"status": 200, "has_matches": has_matches, "html_len": len(html)}
            else:
                results[g] = {"status": r.status_code}
        except Exception as e:
            results[g] = {"error": str(e)}

print(json.dumps(results, indent=2))
