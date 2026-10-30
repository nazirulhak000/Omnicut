import urllib.request
import re
import json

url = 'https://vt.tiktok.com/ZS9ykaGuy492W-oNdZy/'
req = urllib.request.Request(
    url,
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'th-TH,th;q=0.9,en;q=0.8'
    }
)

try:
    with urllib.request.urlopen(req) as resp:
        final_url = resp.geturl()
        print('Final URL:', final_url)
        content = resp.read().decode('utf-8', errors='ignore')
        
        titles = re.findall(r'<title>(.*?)</title>', content, re.IGNORECASE)
        print('Title:', titles)
        
        meta_tags = re.findall(r'<meta\s+([^>]+)>', content)
        for m in meta_tags:
            if 'og:' in m or 'description' in m or 'title' in m:
                print('Meta:', m)
                
        # Check for json blobs like SIGI_STATE or __UNIVERSAL_DATA_FOR_REHYDRATION__
        sigi = re.findall(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', content)
        if sigi:
            print('Found UNIVERSAL_DATA_FOR_REHYDRATION')
            data = json.loads(sigi[0])
            with open('.tmp/tiktok_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print('Saved to .tmp/tiktok_data.json')
        else:
            with open('.tmp/tiktok_page.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print('Saved raw HTML to .tmp/tiktok_page.html')

except Exception as e:
    print('Error:', e)
