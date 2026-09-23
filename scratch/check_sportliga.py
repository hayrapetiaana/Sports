import urllib.request
import ssl
import json
import socket

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

hosts = [
    'www.sport-liga.pro',
    'sport-liga.pro',
    'api.sport-liga.pro',
    'tt.sport-liga.pro',
]

for h in hosts:
    try:
        ip = socket.gethostbyname(h)
        print(f"{h} -> {ip}")
    except Exception as e:
        print(f"{h} -> DNS error: {e}")

# Check what the challenge script on sport-liga.pro does
url = 'https://www.sport-liga.pro/en/table-tennis?date=2026-09-18'
try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        print("sport-liga.pro HTML:")
        print(html)
except Exception as e:
    print(f"Error fetching {url}: {e}")
