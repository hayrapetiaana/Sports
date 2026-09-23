import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('scratch/build_frontend.py', 'r', encoding='utf-8') as f:
    text = f.read()

print("build_frontend.py length:", len(text))

# Search for getCountryBadgeHtml
c_start = text.find('function getCountryBadgeHtml')
c_end = text.find('// Helper: Platform badge', c_start)
if c_end == -1:
    c_end = c_start + 1500
print("--- Country badge function ---")
print(text[c_start:c_end])
