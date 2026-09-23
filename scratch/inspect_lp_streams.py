from bs4 import BeautifulSoup
import httpx

url = "https://liquipedia.net/dota2/api.php?action=parse&page=Liquipedia:Matches&format=json"
r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
data = r.json()
html = data["parse"]["text"]["*"]
soup = BeautifulSoup(html, "html.parser")

match_divs = soup.find_all(class_="match-info")
if match_divs:
    m = match_divs[0]
    print("--- TOURNAMENT AND LINKS SECTION ---")
    tourn = m.find(class_=lambda x: x and "tournament" in x.lower())
    if tourn:
        print("Tournament element:", tourn.prettify())
    links = m.find(class_=lambda x: x and "links" in x.lower())
    if links:
        print("Links element:", links.prettify())

    # Let's check live streams across other matches
    print("\n--- STREAMS ACROSS ALL MATCHES ---")
    found_streams = 0
    for idx, md in enumerate(match_divs):
        for a in md.find_all("a", href=True):
            href = a["href"]
            if any(k in href for k in ["twitch.tv", "youtube.com", "kick.com", "stream", "live", "watch"]):
                print(f"Match {idx} Stream: {href}, text: {a.get_text(strip=True)}")
                found_streams += 1
                if found_streams >= 5:
                    break
        if found_streams >= 5:
            break
    print(f"Total streams checked.")
