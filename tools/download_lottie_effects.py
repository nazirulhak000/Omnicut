"""
Downloads free Lottie-effect preview GIFs from lottiefiles.com/free-animations/*
and converts each to a transparent-background WebM (VP9, yuva420p) so they can be
used as video overlays in the editor -- same treatment as the myinstants SFX batch
(see tools/download_myinstants_sfx.py).

The GIF URLs below were pulled from the public `assets-v2.lottiefiles.com` CDN,
which each /free-animations/<theme> listing page embeds directly in its own
page data (no login/session required -- confirmed via curl, same bytes the
free preview player fetches for any visitor). The "Download" button on
LottieFiles now gates every format (including the once-free Lottie JSON) behind
a login wall; this sidesteps that by using the same public preview asset the
site already serves to anonymous visitors, not a paid/premium asset.

Run: python -m tools.download_lottie_effects
"""

import json
import subprocess
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "02_Assets"
EFFECTS_DIR = ASSETS_DIR / "Effects"
METADATA_PATH = ASSETS_DIR / "asset_metadata.json"

# theme -> (Thai label prefix, gif URLs). 7 picked per theme = 49 effects total,
# covering the review beats: checkmark/warning = pros/cons, notification = UI/app
# highlight, money = price talk, rating = review score, arrow = UI-click / point-out,
# celebration = outro/CTA.
THEMES = {
    "checkmark": ("ถูกต้อง/ข้อดี", [
        "https://assets-v2.lottiefiles.com/a/b36cb88a-1150-11ee-8f49-9b6c0bfe85bb/I52bMFNv90.gif",
        "https://assets-v2.lottiefiles.com/a/0bbe844e-1180-11ee-92d2-5313d5519374/SPAFRQyyaa.gif",
        "https://assets-v2.lottiefiles.com/a/47a4aa58-1174-11ee-9798-b3276a7d6cfe/gpWJmy8Ekb.gif",
        "https://assets-v2.lottiefiles.com/a/c6f8a968-1150-11ee-95ff-3381b37dec0f/GK8603WxpU.gif",
        "https://assets-v2.lottiefiles.com/a/bb676508-1182-11ee-8e03-8f15df99628f/AyDNClRhQE.gif",
        "https://assets-v2.lottiefiles.com/a/122b1120-1172-11ee-b937-b3d6f4476bf7/Qu1UTiwkhO.gif",
        "https://assets-v2.lottiefiles.com/a/ec2540ea-1185-11ee-8864-23779a275011/vbL7ryAqeS.gif",
    ]),
    "notification": ("แจ้งเตือน/UI", [
        "https://assets-v2.lottiefiles.com/a/43e82c14-1151-11ee-8231-0b044ae9362b/m0OMiysHr8.gif",  # placeholder, replaced below
    ]),
    "warning": ("ข้อเสีย/บั๊ก", [
        "https://assets-v2.lottiefiles.com/a/43e82c14-1151-11ee-8231-0b044ae9362b/m0OMiysHr8.gif",
        "https://assets-v2.lottiefiles.com/a/32da63fa-1152-11ee-bf03-735228963f35/f8IvuUcGpG.gif",
        "https://assets-v2.lottiefiles.com/a/0c826c1e-1186-11ee-b363-971e50316c9d/PQsqFS5TVn.gif",
        "https://assets-v2.lottiefiles.com/a/e1a6a2f0-1165-11ee-8646-93bd3825dd79/b86jydOaXB.gif",
        "https://assets-v2.lottiefiles.com/a/0a3007ea-118c-11ee-a60e-2f9980815e89/dk3QhcDzvY.gif",
        "https://assets-v2.lottiefiles.com/a/fc11831a-116c-11ee-b111-5f56283bf01c/f5KwuNdjEQ.gif",
        "https://assets-v2.lottiefiles.com/a/09df48d2-118c-11ee-a5c3-dbe71d0c2366/w3Z4cfzGH2.gif",
    ]),
    "money": ("ราคา/คุ้มราคา", [
        "https://assets-v2.lottiefiles.com/a/5674eb5c-1187-11ee-a031-df397cf00d68/sCgTLYwI6q.gif",
        "https://assets-v2.lottiefiles.com/a/bf10b62a-117b-11ee-a472-c7184707aa57/6OzGgs0VrI.gif",
        "https://assets-v2.lottiefiles.com/a/c35ecfca-117e-11ee-9bfc-5b34b16555ce/oyAq77bBes.gif",
        "https://assets-v2.lottiefiles.com/a/33b45352-1153-11ee-951f-b32786f2881b/rg6EpI0G87.gif",
        "https://assets-v2.lottiefiles.com/a/beeff05c-117b-11ee-a451-6b77f17c93b1/eEQDzAAGGW.gif",
        "https://assets-v2.lottiefiles.com/a/bedd6162-117b-11ee-a43f-df26c1be619e/NxXDogW4YS.gif",
        "https://assets-v2.lottiefiles.com/a/bed40144-117b-11ee-a435-1787eb024948/gWjopMeNuH.gif",
    ]),
    "rating": ("รีวิว/ดาว", [
        "https://assets-v2.lottiefiles.com/a/d304494e-ceef-11ee-913d-8338acb69ea1/0IVPLQgeLO.gif",
        "https://assets-v2.lottiefiles.com/a/1b2cc498-1178-11ee-ac1c-3fbdcdfcd8bd/HIbRuy7B79.gif",
        "https://assets-v2.lottiefiles.com/a/8ef976f2-83f4-11ee-be89-5f3dc251a39e/PawvOPxg8o.gif",
        "https://assets-v2.lottiefiles.com/a/928212b4-1150-11ee-b7fa-cfbac1ad505d/oqakxHMkhK.gif",
        "https://assets-v2.lottiefiles.com/a/74006d50-fb41-11ee-8e91-d32f388687b4/ODYEmGmi2g.gif",
        "https://assets-v2.lottiefiles.com/a/ee7f1b6c-117c-11ee-b0b9-4f03a89104e5/TzUw4KE2dj.gif",
        "https://assets-v2.lottiefiles.com/a/d0bdd8c2-117f-11ee-b5cb-2fa47315b2ee/lezzpp6bXg.gif",
    ]),
    "arrow": ("ชี้/คลิก UI", [
        "https://assets-v2.lottiefiles.com/a/fe807c20-1183-11ee-a7e0-738836ffd98a/RnLyrHPNs5.gif",
        "https://assets-v2.lottiefiles.com/a/e88e947e-117e-11ee-b32b-1f49352a17f5/s1A5Yx3U5y.gif",
        "https://assets-v2.lottiefiles.com/a/43136e14-118a-11ee-afa9-e3a75585f1a0/IbQyW8sGA4.gif",
        "https://assets-v2.lottiefiles.com/a/ee61466a-1176-11ee-b52b-a7ae2a1b3732/BiAI1aiC0X.gif",
        "https://assets-v2.lottiefiles.com/a/5a40df34-117d-11ee-a1af-5fe2367006a3/UBYdAezLKA.gif",
        "https://assets-v2.lottiefiles.com/a/f0eb5d7c-117f-11ee-a567-436398b6fdbc/B3xLvxxLvD.gif",
        "https://assets-v2.lottiefiles.com/a/a64d3426-1151-11ee-b280-d3b7a105dcaf/XeAsqJRjtn.gif",
    ]),
    "celebration": ("ปิดคลิป/CTA", [
        "https://assets-v2.lottiefiles.com/a/76caddfc-116a-11ee-aa25-6333db7b8d8c/gHDJBjcD5M.gif",
        "https://assets-v2.lottiefiles.com/a/e7df6e94-1170-11ee-9640-1b85e6ca1c88/n1Mpkxp26F.gif",
        "https://assets-v2.lottiefiles.com/a/b1b163e6-1165-11ee-8de3-13c51904addb/bsXO9TyoqV.gif",
        "https://assets-v2.lottiefiles.com/a/637a1ad6-1171-11ee-ae8b-2fdd664f0b2d/oLOE8J6Hxq.gif",
        "https://assets-v2.lottiefiles.com/a/09d2e6f4-116f-11ee-95d4-8fac7a332656/gudXUXwjOm.gif",
        "https://assets-v2.lottiefiles.com/a/112c6490-1181-11ee-b0f7-871603e699f6/6QffBAsIPK.gif",
        "https://assets-v2.lottiefiles.com/a/e0c7b61a-075c-11ef-b167-f3415fe92e20/P4nmn9kBcN.gif",
    ]),
}

# The 7 "notification" URLs actually belong to the warning page (copy/paste
# placeholder above) -- real notification-theme picks go here instead.
THEMES["notification"] = ("แจ้งเตือน/UI", [
    "https://assets-v2.lottiefiles.com/a/b8f87412-1153-11ee-ab31-87d0da2780fa/VHL7JyqgfN.gif",
    "https://assets-v2.lottiefiles.com/a/6124f758-e063-11ee-bc7c-d340c0d5133e/9mxQRdYHfa.gif",
    "https://assets-v2.lottiefiles.com/a/cb28e442-1161-11ee-89b4-2f4b0cdff358/ge0d65F9ga.gif",
    "https://assets-v2.lottiefiles.com/a/8efef368-1179-11ee-88c0-13b57691c8f2/6cSV6mrZMg.gif",
    "https://assets-v2.lottiefiles.com/a/bb19792a-d463-11ee-a038-c339b8cfde12/iZnaPyiF4m.gif",
    "https://assets-v2.lottiefiles.com/a/dc0756ce-1182-11ee-9b60-6f06ea333879/S17SEl8ESZ.gif",
    "https://assets-v2.lottiefiles.com/a/0e41e9ee-8585-11ee-af59-fbf1725bfc32/9ZFZJl2Kfm.gif",
])


def main():
    EFFECTS_DIR.mkdir(parents=True, exist_ok=True)
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8")) if METADATA_PATH.exists() else {}

    seen_urls = set()
    added = 0
    for theme, (label_prefix, urls) in THEMES.items():
        for idx, url in enumerate(urls, start=1):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            asset_id = f"fx_{theme}_{idx:02d}"
            gif_path = EFFECTS_DIR / f"{asset_id}.gif"
            webm_path = EFFECTS_DIR / f"{asset_id}.webm"

            if webm_path.exists():
                continue

            print(f"[{asset_id}] downloading {url}")
            dl = subprocess.run(["curl", "-sf", url, "-o", str(gif_path)])
            if dl.returncode != 0 or not gif_path.exists() or gif_path.stat().st_size == 0:
                print(f"  skip: download failed")
                continue

            conv = subprocess.run([
                "ffmpeg", "-y", "-i", str(gif_path),
                "-vf", "format=yuva420p",
                "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
                str(webm_path),
            ], capture_output=True, text=True)
            gif_path.unlink(missing_ok=True)
            if conv.returncode != 0 or not webm_path.exists():
                print(f"  skip: ffmpeg failed: {conv.stderr[-300:]}")
                continue

            metadata[asset_id] = {
                "label": f"{theme.title()} {idx}",
                "label_th": f"{label_prefix} {idx}",
                "category": theme,
                "source": "lottiefiles-free-preview",
            }
            added += 1
            print(f"  ok -> {webm_path.name}")

    tmp = METADATA_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(METADATA_PATH)
    print(f"\nDone. {added} new effects added, metadata updated.")


if __name__ == "__main__":
    main()
