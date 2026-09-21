import urllib.request
import re

urls = [
    ("Redmi_redmi_note_13_pro_plus", "https://www.mi.com/global/product/redmi-note-13-pro-plus-5g/"),
    ("POCO_poco_f6_pro", "https://www.po.co/global/product/poco-f6-pro/"),
    ("POCO_poco_x6_pro", "https://www.po.co/global/product/poco-x6-pro/"),
    ("Xiaomi_xiaomi_smart_band_9", "https://www.mi.com/global/product/xiaomi-smart-band-9/"),
    ("Xiaomi_xiaomi_watch_s4", "https://www.mi.com/global/product/xiaomi-watch-s3/"),
    ("Xiaomi_xiaomi_robot_vacuum_x20_max", "https://www.mi.com/global/product/xiaomi-robot-vacuum-x20-max/"),
    ("Xiaomi_xiaomi_air_compressor_2", "https://www.mi.com/global/product/xiaomi-portable-electric-air-compressor-2/"),
    ("Xiaomi_xiaomi_smart_air_purifier_4", "https://www.mi.com/global/product/xiaomi-smart-air-purifier-4/"),
]

for name, url in urls:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
        og = re.findall(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
        if not og:
            og = re.findall(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html)
        print(f"{name:<35} -> {og[0] if og else 'NOT FOUND'}")
    except Exception as e:
        print(f"{name:<35} -> ERROR: {e}")
