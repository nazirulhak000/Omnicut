import re
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('.tmp/pdp_tiktok.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Look for __UNIVERSAL_DATA_FOR_REHYDRATION__ or script tags with product details
scripts = re.findall(r'<script id="RENDER_DATA"[^>]*>(.*?)</script>', html, re.DOTALL)
if not scripts:
    scripts = re.findall(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.DOTALL)
if not scripts:
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

print(f"Examining {len(scripts)} scripts...")
product_info = {}
for i, s in enumerate(scripts):
    if 'product_id' in s or 'title' in s or 'gallery' in s or '30000' in s:
        print(f"Script {i} matches keywords (len={len(s)})")
        try:
            # check if it is json
            data = json.loads(s.strip())
            with open(f'.tmp/pdp_script_{i}.json', 'w', encoding='utf-8') as sf:
                json.dump(data, sf, ensure_ascii=False, indent=2)
            print(f"Saved .tmp/pdp_script_{i}.json")
        except Exception:
            pass

# Also grab all 800:800 images
imgs_800 = list(set(re.findall(r'https://[^\s\"\'<>]+\.ibyteimg\.com/[^\s\"\'<>]+resize-webp:800:800\.webp[^\s\"\'<>]*', html)))
print(f"Found {len(imgs_800)} 800x800 images:")
for u in imgs_800:
    clean_u = u.replace('&amp;', '&')
    print(' ', clean_u)

with open('.tmp/pdp_gallery_urls.json', 'w', encoding='utf-8') as f:
    json.dump([u.replace('&amp;', '&') for u in imgs_800], f, indent=2)
