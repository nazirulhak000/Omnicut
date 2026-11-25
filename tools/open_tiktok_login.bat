@echo off
rem เปิด Chrome โปรไฟล์ของ autopost ค้างไว้ให้ login TikTok ด้วยมือ (ไม่ต้องปิดหน้าต่างหลัง login)
cd /d "%~dp0\.."
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9333 --user-data-dir="%CD%\tools\tiktok_browser_profile" --no-first-run https://www.tiktok.com/login?redirect_url=https%%3A%%2F%%2Fwww.tiktok.com%%2Ftiktokstudio%%2Fupload
