import urllib.request
import urllib.parse
import re
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'th,en;q=0.9'
}

queries = [
    "K106 30000mah power bank 22.5W magnetic",
    "TTZ K106 30000mah power bank",
    "power bank 30000mah ชาร์จเร็ว 22.5W มีสาย Lightning Type-c wireless charge"
]

found_images = set()

for q in queries:
    url = f"https://www.bing.com/images/search?q={urllib.parse.quote(q)}&FORM=HDRSC2"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            # Extract murl from bing: murl&quot;:&quot;(http[^&]+)&quot;
            murls = re.findall(r'murl&quot;:&quot;(https?://[^&]+)&quot;', html)
            print(f"Query '{q}': found {len(murls)} images")
            for m in murls:
                found_images.add(m)
    except Exception as e:
        print(f"Error for query '{q}':", e)

print(f"Total unique images found: {len(found_images)}")
with open('.tmp/bing_images.json', 'w', encoding='utf-8') as f:
    json.dump(list(found_images), f, indent=2)
