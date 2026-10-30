import json
import urllib.request
import os

with open('.tmp/pdp_gallery_urls.json', 'r', encoding='utf-8') as f:
    urls = json.load(f)

print(f"Total URLs: {len(urls)}")
out_dir = ".tmp/product_inspect/gallery"
os.makedirs(out_dir, exist_ok=True)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

saved_files = []
for i, url in enumerate(urls[:10], 1):
    path = os.path.join(out_dir, f"img_{i:02d}.webp")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp, open(path, 'wb') as f:
            f.write(resp.read())
        print(f"Downloaded {path} ({os.path.getsize(path)} bytes)")
        saved_files.append(path)
    except Exception as e:
        print(f"Error {url}: {e}")

print("Saved files:", saved_files)
