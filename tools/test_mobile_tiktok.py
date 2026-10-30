import urllib.request
import re
import json

url = 'https://vt.tiktok.com/ZS9ykaGuy492W-oNdZy/'
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 musical_ly_31.0.0'
}
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        print('Final URL:', resp.geturl())
        html = resp.read().decode('utf-8', errors='ignore')
        print('Length:', len(html))
        imgs = set(re.findall(r'https://[^\s\"\'<>]+\.ibyteimg\.com/[^\s\"\'<>]+', html))
        print('TikTok images:', len(imgs))
        for img in list(imgs)[:10]:
            print('  ', img)
        with open('.tmp/mobile_tiktok.html', 'w', encoding='utf-8') as f:
            f.write(html)
except Exception as e:
    print('Error:', e)
