import re

with open('.tmp/tiktok_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

print('Length of html:', len(text))
img_urls = set(re.findall(r'https://[^\s\"\'<>]+\.(?:webp|jpeg|jpg|png)[^\s\"\'<>]*', text))
print('Found image URLs:', len(img_urls))
for u in list(img_urls)[:30]:
    print('  ', u)

scripts = re.findall(r'<script[^>]*>(.*?)</script>', text, re.DOTALL)
print('Found script tags:', len(scripts))
for i, s in enumerate(scripts):
    if len(s) > 100:
        print(f'Script {i} length: {len(s)}, preview: {s[:100]}...')
