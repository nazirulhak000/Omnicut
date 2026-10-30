import urllib.request
import os

img_url = "https://p16-oec-sg.ibyteimg.com/tos-alisg-i-aphluv4xwc-sg/35078db76d5d45bebb6659a25542d7c9~tplv-aphluv4xwc-resize-jpeg:800:800.jpeg"
os.makedirs(".tmp/product_inspect", exist_ok=True)
out_path = ".tmp/product_inspect/thumb_800.jpg"

try:
    req = urllib.request.Request(
        img_url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req) as resp, open(out_path, 'wb') as f:
        f.write(resp.read())
    print("Downloaded 800x800 image to", out_path)
except Exception as e:
    print("Error:", e)
