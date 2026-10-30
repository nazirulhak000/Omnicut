import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
import re
import json

url = 'https://shopee.co.th/%E0%B8%9E%E0%B8%B2%E0%B8%A7%E0%B9%80%E0%B8%A7%E0%B8%AD%E0%B8%A3%E0%B9%8C%E0%B9%81%E0%B8%9A%E0%B8%87%E0%B8%84%E0%B9%8C%E0%B9%84%E0%B8%A3%E0%B9%89%E0%B8%AA%E0%B8%B2%E0%B8%A2-30000mah-%E0%B8%8B%E0%B8%B2%E0%B8%A3%E0%B9%8C%E0%B8%88%E0%B9%80%E0%B8%A3%E0%B9%87%E0%B8%A7-22.5W-Magnetic-Powerbank-%E0%B8%82%E0%B8%B2%E0%B8%95%E0%B8%B1%E0%B9%89%E0%B8%87%E0%B9%81%E0%B8%9A%E0%B8%9A%E0%B8%9E%E0%B8%81%E0%B8%9E%E0%B8%B2-%E0%B8%97%E0%B8%B5%E0%B9%88%E0%B8%8A%E0%B8%B2%E0%B8%A3%E0%B9%8C%E0%B8%88%E0%B9%84%E0%B8%A3%E0%B9%89%E0%B8%AA%E0%B8%B2%E0%B8%A2-%E0%B9%81%E0%B8%9A%E0%B8%95%E0%B8%AA%E0%B8%B3%E0%B8%A3%E0%B8%AD%E0%B8%87%E0%B9%84%E0%B8%A3%E0%B9%89%E0%B8%AA%E0%B8%B2%E0%B8%A2-i.1683395652.48804667828'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    )
    try:
        page.goto(url, timeout=30000)
        page.wait_for_timeout(4000)
        print('Page title:', page.title())
        html = page.content()
        # Find shopee cdn image hashes (down-th.img.susercontent.com/file/...)
        shopee_imgs = set(re.findall(r'https://[^\s\"\'<>]+\.susercontent\.com/file/[a-zA-Z0-9_-]+', html))
        print(f'Found {len(shopee_imgs)} shopee images')
        for img in list(shopee_imgs)[:20]:
            print(' ', img)
        with open('.tmp/shopee_images.json', 'w', encoding='utf-8') as f:
            json.dump(list(shopee_imgs), f, indent=2)
    except Exception as e:
        print('Error:', e)
    browser.close()
