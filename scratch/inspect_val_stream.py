import httpx
from bs4 import BeautifulSoup

url = "https://liquipedia.net/valorant/api.php?action=parse&page=Liquipedia:Matches&format=json"
r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
html = r.json().get("parse", {}).get("text", {}).get("*", "")
soup = BeautifulSoup(html, "html.parser")

for a in soup.find_all("a", href=True):
    if "Special:Stream" in a["href"]:
        print("Found stream link:", a["href"])
        print("Parent container:", a.parent.prettify()[:500])
        # Find closest match-info
        match = a.find_parent(class_="match-info")
        if match:
            print("Found in match-info:", match.find(class_="match-info-header").get_text(separator=" ", strip=True))
        break
