with open('static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

builder_content = f'''import os

# Build the complete updated static/index.html
frontend_code = r\'\'\'{html}\'\'\'

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(frontend_code)

print("Successfully written static/index.html with all 5 sections, timezone engine, Liga Pro branding, and SVG country flags!")
'''

with open('scratch/build_frontend.py', 'w', encoding='utf-8') as f:
    f.write(builder_content)

print("scratch/build_frontend.py synced with static/index.html!")
