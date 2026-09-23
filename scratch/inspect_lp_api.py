import httpx
import json
from bs4 import BeautifulSoup

def inspect_lp_api():
    games = ["dota2", "counterstrike", "valorant"]
    for game in games:
        api_url = f"https://liquipedia.net/{game}/api.php?action=parse&page=Liquipedia:Matches&format=json"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        with httpx.Client(headers=headers, timeout=15) as client:
            r = client.get(api_url)
            print(f"[{game}] Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                html = data.get("parse", {}).get("text", {}).get("*", "")
                print(f"[{game}] HTML length: {len(html)}")
                soup = BeautifulSoup(html, "html.parser")
                # Look for match tables or match containers
                matches = soup.find_all("table", class_="infobox_matches_content")
                if not matches:
                    matches = soup.find_all(class_=lambda x: x and "match" in x.lower())
                print(f"[{game}] Matched elements: {len(matches)}")
                
                # Check team names, initials, formats, streams
                sample_tables = soup.find_all("table", class_="infobox_matches_content")
                if sample_tables:
                    t = sample_tables[0]
                    print(f"[{game}] Sample table text snippet: {t.get_text(separator=' ', strip=True)[:200]}")
                    with open(f"scratch/sample_{game}_match.html", "w", encoding="utf-8") as f:
                        f.write(str(t))

if __name__ == "__main__":
    inspect_lp_api()
