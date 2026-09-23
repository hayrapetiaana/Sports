from bs4 import BeautifulSoup
import httpx

url = "https://liquipedia.net/dota2/api.php?action=parse&page=Liquipedia:Matches&format=json"
r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
data = r.json()
html = data["parse"]["text"]["*"]
soup = BeautifulSoup(html, "html.parser")

match_divs = soup.find_all(class_="match-info")
print(f"Found {len(match_divs)} match-info elements!")

if match_divs:
    m = match_divs[0]
    print("\n--- SAMPLE MATCH-INFO HTML ---")
    print(m.prettify()[:2500])
