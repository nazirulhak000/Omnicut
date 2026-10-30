import urllib.request
import urllib.parse
import json
import re

query = "K106 30000mAh Magnetic Power Bank"
url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"

req = urllib.request.Request(
    url,
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
)

try:
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        # Find links
        links = re.findall(r'href=\"(https?://[^\"]+)\"', html)
        print(f"Found {len(links)} links")
        for l in links[:15]:
            if 'uddg=' in l:
                actual = urllib.parse.unquote(l.split('uddg=')[1].split('&')[0])
                print('  Link:', actual)
            else:
                print('  Direct:', l)
except Exception as e:
    print("Error:", e)
