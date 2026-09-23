import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="section-ttcup"')
if idx != -1:
    print(text[idx:idx+1200])
else:
    print("Not found")
