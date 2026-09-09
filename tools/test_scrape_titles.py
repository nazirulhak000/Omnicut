import urllib.request
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

url = "https://www.myinstants.com/en/index/th/?page=1"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/127.0.0.0"}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode("utf-8", errors="replace")

# Match each instant block
blocks = re.findall(r'<div class="instant.*?</div>\s*</div>', html, re.DOTALL)
print(f"Matched blocks: {len(blocks)}")

# Let's inspect small-button and link
for b in blocks[:15]:
    m_sound = re.search(r"/media/sounds/([a-zA-Z0-9_\-\.%]+\.mp3)", b)
    m_title = re.search(r'class="instant-link[^"]*"[^>]*>(.*?)</a>', b, re.DOTALL)
    if m_sound and m_title:
        print(f"mi_{m_sound.group(1)}  ==>  {m_title.group(1).strip()}")
