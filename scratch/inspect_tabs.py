import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('unified-status-tab-all')
if idx != -1:
    print(text[idx-100:idx+900])
else:
    print("Not found")
