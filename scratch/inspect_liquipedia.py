import httpx
import re

url = "https://liquipedia.net/dota2/Liquipedia:Matches"
headers = {
    "User-Agent": "TTParserEsports/1.0 (https://github.com/hayran; esports@parser.local) Mozilla/5.0",
    "Accept-Encoding": "gzip, deflate"
}

try:
    with httpx.Client(headers=headers, follow_redirects=True, timeout=15) as client:
        r = client.get(url)
        print("Status code:", r.status_code)
        print("Final URL:", r.url)
        html = r.text
        print("HTML length:", len(html))
        with open("scratch/sample_liquipedia_dota.html", "w", encoding="utf-8") as f:
            f.write(html[:50000])
        print("Saved snippet to scratch/sample_liquipedia_dota.html")
except Exception as e:
    print("Error:", type(e), e)
