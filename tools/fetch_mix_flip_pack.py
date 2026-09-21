import urllib.request
import re
import json
import os
import subprocess
from pathlib import Path

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

dest_dir = Path(r"d:\Winona\Programmer\Capcut\.tmp\gadget_products\Xiaomi_xiaomi_mix_flip")
photos_dir = dest_dir / "photos"
inserts_dir = dest_dir / "inserts"
photos_dir.mkdir(parents=True, exist_ok=True)
inserts_dir.mkdir(parents=True, exist_ok=True)

print(f"Target directories prepared: {photos_dir}, {inserts_dir}")

# 1. GSMArena pictures
try:
    search_url = "https://www.gsmarena.com/results.php3?sQuickSearch=yes&sName=xiaomi+mix+flip"
    req = urllib.request.Request(search_url, headers=headers)
    html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
    links = re.findall(r'href="([^"]*xiaomi_mix_flip[^"]*)"', html)
    print("GSM links found:", links)
    
    target_link = None
    for l in links:
        if "pictures" in l or "13" in l:
            target_link = l
            break
    if not target_link and links:
        target_link = links[0].replace(".php", "-pictures.php")
        
    if target_link:
        if not target_link.startswith("http"):
            target_link = "https://www.gsmarena.com/" + target_link
        print("Fetching pictures from:", target_link)
        req2 = urllib.request.Request(target_link, headers=headers)
        pic_html = urllib.request.urlopen(req2, timeout=15).read().decode('utf-8', errors='ignore')
        img_urls = re.findall(r'src="(https://fdn\d?\.gsmarena\.com/vv/pics/xiaomi/[^"]+)"', pic_html)
        img_urls += re.findall(r'href="(https://fdn\d?\.gsmarena\.com/vv/pics/xiaomi/[^"]+)"', pic_html)
        img_urls += re.findall(r'src="(https://fdn\d?\.gsmarena\.com/imgroot/reviews/[^"]+)"', pic_html)
        print(f"Found {len(img_urls)} GSM images")
        
        for idx, u in enumerate(set(img_urls)):
            # convert thumbnail to full res if possible
            full_u = u.replace("-3.", "-1.").replace("thumb/", "")
            fname = f"gsmarena_mix_flip_{idx+1}.jpg"
            fpath = photos_dir / fname
            if not fpath.exists():
                try:
                    urllib.request.urlretrieve(full_u, fpath)
                    print(f"Downloaded: {fname}")
                except Exception as e:
                    try:
                        urllib.request.urlretrieve(u, fpath)
                        print(f"Downloaded thumb: {fname}")
                    except:
                        pass
except Exception as e:
    print(f"GSM error: {e}")

# 2. Mi.com Official page images
try:
    mi_url = "https://www.mi.com/global/product/xiaomi-mix-flip/specs/"
    req = urllib.request.Request(mi_url, headers=headers)
    mi_html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
    mi_imgs = re.findall(r'(https://i02\.appmifile\.com/[^"\')\s]+)', mi_html)
    print(f"Found {len(mi_imgs)} mi.com images")
    for idx, u in enumerate(set(mi_imgs)[:10]):
        ext = ".png" if ".png" in u else ".jpg"
        clean_u = u.split("?")[0]
        fname = f"micom_official_spec_{idx+1}{ext}"
        fpath = photos_dir / fname
        if not fpath.exists():
            try:
                urllib.request.urlretrieve(clean_u, fpath)
                print(f"Downloaded mi.com: {fname}")
            except Exception as e:
                pass
except Exception as e:
    print(f"Mi.com error: {e}")

# 3. Download YouTube B-roll / insert clips (Clean / Official)
video_targets = [
    {
        "id": "Uz-xREb9_Ck",
        "name": "insert_official_fliptastic_design.mp4",
        "desc": "Official Xiaomi MIX Flip design teaser 1080p (clean)"
    },
    {
        "id": "SmcchZGeFnk",
        "name": "insert_official_unboxing_fan.mp4",
        "desc": "Official Xiaomi Fan Unboxing hands-on (clean)"
    },
    {
        "id": "pJeo3o2OZVM",
        "name": "insert_hands_on_asmr_black.mp4",
        "desc": "Clean ASMR hands-on black edition folding/unfolding"
    }
]

for vt in video_targets:
    target_path = inserts_dir / vt["name"]
    if not target_path.exists():
        print(f"Downloading B-roll: {vt['name']} ({vt['desc']})...")
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "--merge-output-format", "mp4",
            f"https://www.youtube.com/watch?v={vt['id']}",
            "-o", str(target_path)
        ]
        # if the video is long (like pJeo3o2OZVM which is 7 mins), download only first 60 seconds
        if vt["id"] == "pJeo3o2OZVM":
            cmd = [
                "yt-dlp",
                "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
                "--download-sections", "*00:00-01:30",
                "--merge-output-format", "mp4",
                f"https://www.youtube.com/watch?v={vt['id']}",
                "-o", str(target_path)
            ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if target_path.exists():
                print(f"Successfully downloaded {vt['name']} ({target_path.stat().st_size} bytes)")
            else:
                print(f"Failed to download {vt['name']}: {res.stderr[:200]}")
        except Exception as e:
            print(f"Error downloading {vt['name']}: {e}")

print("\n--- ALL ASSETS HARVESTED ---")
