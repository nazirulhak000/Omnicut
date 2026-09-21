import urllib.request
import re

def get_page_images(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
    # Find all appmifile or mi-img urls
    found = set(re.findall(r'(?:https?:)?//(?:i0\d\.appmifile\.com|cdn\.cnbj\d\.fds\.api\.mi-img\.com)[^\s"\'\(\)]+\.(?:png|jpg|webp)', html))
    return sorted(list(found))

if __name__ == "__main__":
    imgs = get_page_images("https://www.mi.com/global/product/xiaomi-mix-flip/")
    print(f"Found {len(imgs)} images:")
    for img in imgs[:10]:
        print(img)
