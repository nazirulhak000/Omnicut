import urllib.request
import re
import json

url = 'https://shop.tiktok.com/th/pdp/1734525733612521290'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'th,en;q=0.9'
}
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        print('Status:', resp.status, 'HTML length:', len(html))
        imgs = set(re.findall(r'https://[^\s\"\'<>]+\.ibyteimg\.com/[^\s\"\'<>]+', html))
        print('Found images:', len(imgs))
        for img in list(imgs)[:20]:
            print('  ', img)
        with open('.tmp/pdp_tiktok.html', 'w', encoding='utf-8') as f:
            f.write(html)
except Exception as e:
    print('Error:', e)
