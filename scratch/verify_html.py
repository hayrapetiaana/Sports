import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Check function
print("Has Russia:", "title=\"Russia" in text)
print("Has Belarus:", "title=\"Belarus" in text)
print("Has Moldova:", "title=\"Moldova" in text)
print("Has Czech:", "title=\"Czech Republic\"" in text)
print("Has Poland:", "title=\"Poland\"" in text)
print("Has Ukraine:", "title=\"Ukraine\"" in text)

print("Title:", "<title>TT Multi-Monitor — Setka Cup, TT Cup, League Pro & Liga Pro</title>" in text)
print("Subtitle:", "id=\"app-main-subtitle\">Setka Cup • TT Cup • League Pro • Liga Pro</p>" in text)
print("Tab Liga Pro:", "<span>Liga Pro</span>" in text)
print("Platform badge Liga Pro:", "<span class=\"w-1.5 h-1.5 rounded-full bg-rose-400\"></span> Liga Pro" in text)
print("Card header countryBadge:", "${timeDisplay}</span>\n                  ${countryBadge}" in text or "${timeDisplay}</span>\r\n                  ${countryBadge}" in text)

# Check remaining Sport-Liga occurrences
import re
remaining = [m.start() for m in re.finditer(r'Sport[- ]?Liga(?![-.]pro)', text, re.I)]
print(f"Remaining 'Sport-Liga' mentions (excluding URL/domain): {len(remaining)}")
for idx in remaining:
    snippet = text[max(0, idx-30):min(len(text), idx+50)].replace('\n', ' ')
    print(f"  [{idx}]: {snippet}")
