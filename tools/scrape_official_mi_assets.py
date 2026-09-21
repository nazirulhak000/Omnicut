import urllib.request
import re
from pathlib import Path

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

photos_dir = Path(r"d:\Winona\Programmer\Capcut\.tmp\gadget_products\Xiaomi_xiaomi_mix_flip\photos")
photos_dir.mkdir(parents=True, exist_ok=True)

urls = [
    'https://www.mi.com/global/product/xiaomi-mix-flip/',
    'https://www.gsmarena.com/xiaomi_mix_flip-review-2729p2.php',
    'https://www.gsmarena.com/xiaomi_mix_flip-review-2729p3.php',
    'https://www.gsmarena.com/xiaomi_mix_flip-review-2729p5.php'
]

saved_count = 0

for url in urls:
    print(f"Scraping {url}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
        
        # find image links
        img_candidates = re.findall(r'https://[^\s"\'\)<>]+(?:\.jpg|\.png|\.webp)', html)
        print(f"Found {len(img_candidates)} raw image links on {url}")
        
        for u in set(img_candidates):
            # filter for relevant images
            u_clean = u.split('?')[0]
            is_relevant = any(k in u_clean.lower() for k in [
                'mix-flip', 'mix_flip', 'xiaomi', 'appmifile', 'gsmarena'
            ]) and not any(bad in u_clean.lower() for bad in ['vivo', 'poco', 'logo', 'icon', 'banner', 'avatar', 'avatar'])
            
            if is_relevant and ('reviews/24/xiaomi-mix-flip' in u_clean or 'appmifile' in u_clean):
                ext = Path(u_clean).suffix
                fname = f"asset_{abs(hash(u_clean)) % 100000}_{Path(u_clean).name}"
                out_path = photos_dir / fname
                if not out_path.exists():
                    try:
                        r = urllib.request.Request(u, headers=headers)
                        data = urllib.request.urlopen(r, timeout=10).read()
                        if len(data) > 30000: # at least 30KB
                            out_path.write_bytes(data)
                            saved_count += 1
                            print(f"Saved: {fname} ({len(data)} bytes)")
                    except Exception as e:
                        pass
    except Exception as e:
        print(f"Failed {url}: {e}")

print(f"\nFinished! Total new high-res photos saved: {saved_count}")
