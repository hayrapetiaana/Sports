from bs4 import BeautifulSoup
import httpx

url = "https://liquipedia.net/dota2/api.php?action=parse&page=Liquipedia:Matches&format=json"
r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
data = r.json()
html = data["parse"]["text"]["*"]

soup = BeautifulSoup(html, "html.parser")
# Find match containers: Liquipedia usually wraps matches in div with class 'panel_contents' or table or matchlist
matchlists = soup.find_all(class_=lambda x: x and ("matchlist" in x.lower() or "infobox_matches" in x.lower()))
print("Matchlists count:", len(matchlists))

# Let's inspect a few match rows / cards
rows = soup.find_all("table", class_="infobox_matches_content")
print("Infobox matches content count:", len(rows))
if not rows:
    # Look for div match rows
    rows = soup.find_all(class_=lambda x: x and "panel-box" in x.lower())
    print("Panel box count:", len(rows))
if not rows:
    rows = soup.find_all(class_=lambda x: x and ("bracket-game" in x.lower() or "match-row" in x.lower()))
    print("Bracket game count:", len(rows))

# Let's find any element containing 'vs' or team names
print("Sample HTML structure snippet:")
main_div = soup.find("div", class_="mw-parser-output")
if main_div:
    children = [c for c in main_div.children if getattr(c, 'name', None)]
    for idx, c in enumerate(children[:15]):
        print(f"Child {idx}: tag={c.name}, classes={c.get('class', [])}")

# Let's find tables or divs inside
tables = soup.find_all("table")
print(f"Total tables: {len(tables)}")
for i, t in enumerate(tables[:5]):
    print(f"Table {i} class: {t.get('class', [])}, text snippet: {t.get_text(separator=' ', strip=True)[:100]}")
