import urllib.request
import re
from pathlib import Path

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://www.gsmarena.com/'
}

photos_dir = Path(r"d:\Winona\Programmer\Capcut\.tmp\gadget_products\Xiaomi_xiaomi_mix_flip\photos")
photos_dir.mkdir(parents=True, exist_ok=True)

url = 'https://www.gsmarena.com/xiaomi_mix_flip-review-2729.php'
print(f"Connecting to {url}...")
try:
    req = urllib.request.Request(url, headers=headers)
    html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
    
    # Extract all img and picture elements
    img_srcs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html)
    print(f"Total img tags: {len(img_srcs)}")
    print("Sample imgs:", img_srcs[:5])
    
    # Filter for xiaomi pics
    matches = [u for u in img_srcs if "xiaomi" in u or "reviews" in u or "pics" in u]
    unique_urls = list(set(matches))
    print(f"Filtered images: {len(unique_urls)}")
    
    downloaded = 0
    for u in unique_urls:
        if "thumb" in u or "-3.jpg" in u:
            # try to get high-res equivalent
            highres_u = u.replace("-3.jpg", "-1.jpg").replace("/thumb/", "/")
        else:
            highres_u = u
            
        fname = highres_u.split('/')[-1]
        out_file = photos_dir / fname
        if not out_file.exists():
            try:
                r_img = urllib.request.Request(highres_u, headers=headers)
                data = urllib.request.urlopen(r_img, timeout=10).read()
                out_file.write_bytes(data)
                downloaded += 1
                print(f"Saved: {fname} ({len(data)} bytes)")
            except Exception as e:
                # try original url
                try:
                    r_img2 = urllib.request.Request(u, headers=headers)
                    data2 = urllib.request.urlopen(r_img2, timeout=10).read()
                    out_file.write_bytes(data2)
                    downloaded += 1
                    print(f"Saved fallback: {fname} ({len(data2)} bytes)")
                except:
                    pass
    print(f"Successfully downloaded {downloaded} GSMArena photos!")
except Exception as e:
    print(f"Error fetching GSMArena: {e}")
