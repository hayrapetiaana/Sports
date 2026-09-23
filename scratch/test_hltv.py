import httpx

url = "https://www.hltv.org/matches?selectedDate=2026-09-18"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

with httpx.Client(headers=headers, timeout=10) as client:
    r = client.get(url)
    print("HLTV status:", r.status_code)
    print("HLTV title:", r.text[:500] if r.status_code != 200 else "OK")
    if r.status_code == 403:
        with open("scratch/hltv_response.html", "w", encoding="utf-8") as f:
            f.write(r.text)
