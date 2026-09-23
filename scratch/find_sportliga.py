import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('scratch/build_frontend.py', 'r', encoding='utf-8') as f:
    text = f.read()

matches = list(re.finditer(r'Sport[- ]?Liga', text, re.I))
print(f"Total occurrences of Sport-Liga: {len(matches)}")
for i, m in enumerate(matches):
    start = max(0, m.start() - 30)
    end = min(len(text), m.end() + 40)
    snippet = text[start:end].replace('\n', ' ')
    print(f"{i+1}: {snippet}")
