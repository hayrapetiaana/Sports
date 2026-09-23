with open('static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="section-sportliga"')
print("Repr:", repr(text[idx+300:idx+700]))
