import asyncio
import json
import httpx
from bs4 import BeautifulSoup

async def inspect():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html",
    }
    # Check mobilelegends matches
    url = "https://liquipedia.net/mobilelegends/api.php?action=parse&page=Liquipedia:Matches&format=json"
    async with httpx.AsyncClient(headers=headers, timeout=20.0) as client:
        r = await client.get(url)
        print("Status:", r.status_code)
        if r.status_code == 200:
            data = r.json()
            html = data.get("parse", {}).get("text", {}).get("*", "")
            print("HTML length:", len(html))
            soup = BeautifulSoup(html, "html.parser")
            match_divs = soup.find_all(class_="match-info")
            print(f"Found {len(match_divs)} match-info divs")
            
            # Also check if there are other match containers, like tables or divs
            tables = soup.find_all("table")
            print(f"Found {len(tables)} tables")
            
            # Inspect first 3 match-info divs in detail
            for i, m in enumerate(match_divs[:3]):
                print(f"\n--- MATCH {i+1} ---")
                print("Classes:", m.get("class"))
                print("Text snippet:", m.get_text(separator=" ", strip=True)[:200])
                # Check parent elements for tournament info!
                parent = m.parent
                for p_level in range(5):
                    if not parent: break
                    tournament_el = parent.find(class_=lambda c: c and ("tournament" in c or "league" in c or "header" in c))
                    if tournament_el:
                        print(f"Parent level {p_level} has tournament element:", tournament_el.get_text(strip=True)[:100])
                    parent = parent.parent
                
                # Check all links inside match div
                links = [(a.get("title"), a.get("href"), a.get("class")) for a in m.find_all("a")]
                print("Links:", links)
                
                # Check entire HTML of one match div
                if i == 0:
                    with open("scratch/sample_match.html", "w", encoding="utf-8") as f:
                        f.write(m.prettify())
                    print("Saved scratch/sample_match.html")

if __name__ == "__main__":
    asyncio.run(inspect())
