import httpx
from bs4 import BeautifulSoup
import re

for game in ["dota2", "counterstrike", "valorant"]:
    url = f"https://liquipedia.net/{game}/api.php?action=parse&page=Liquipedia:Matches&format=json"
    r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    html = r.json().get("parse", {}).get("text", {}).get("*", "")
    soup = BeautifulSoup(html, "html.parser")
    
    # Check for stream keywords
    stream_tags = soup.find_all(lambda tag: any("stream" in str(v).lower() for v in [tag.get("class"), tag.get("id"), tag.get("data-stream")] if v))
    print(f"[{game}] Tags with 'stream': {len(stream_tags)}")
    for st in stream_tags[:3]:
        print(f"  Tag: {st.name}, class: {st.get('class')}, attrs: {st.attrs}")
    
    # Check all links
    links = [a['href'] for a in soup.find_all("a", href=True) if any(x in a['href'].lower() for x in ['twitch', 'youtube', 'kick', 'trovo', 'stream', 'live'])]
    print(f"[{game}] Stream URLs found: {len(links)}: {links[:3]}")

    # Check match-info-header-scoreholder for live indicators
    live_indicators = soup.find_all(class_=lambda x: x and ("live" in x.lower() or "current" in x.lower()))
    print(f"[{game}] Live indicators: {len(live_indicators)}")
