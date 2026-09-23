from bs4 import BeautifulSoup
import httpx

url = "https://liquipedia.net/dota2/api.php?action=parse&page=Liquipedia:Matches&format=json"
r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
data = r.json()
html = data["parse"]["text"]["*"]
soup = BeautifulSoup(html, "html.parser")

main_div = soup.find("div", class_="mw-parser-output")
classes = set()
for tag in main_div.find_all(True):
    for c in tag.get("class", []):
        classes.add(c)

print("All classes in mw-parser-output (sample):")
match_classes = sorted([c for c in classes if any(k in c.lower() for k in ["match", "team", "versus", "score", "format", "tournament", "stream"])])
print(match_classes[:40])

# Let's inspect the first 3 elements with class containing 'match' or similar
for c in ["match-row", "matches-list", "panel-box", "bracket-popup-body"]:
    elems = soup.find_all(class_=c)
    if elems:
        print(f"Found {len(elems)} with class '{c}'")

# Let's print the first 2 children of main_div in detail
children = [c for c in main_div.children if getattr(c, 'name', None)]
for idx in range(min(5, len(children))):
    c = children[idx]
    print(f"\n--- CHILD {idx}: tag={c.name}, class={c.get('class', [])} ---")
    print(str(c)[:500])
