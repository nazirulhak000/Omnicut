@echo off
setlocal
rem เปิด Chrome โปรไฟล์ของ autopost ค้างไว้ให้ login TikTok ด้วยมือ (ไม่ต้องปิดหน้าต่างหลัง login)
cd /d "%~dp0\.."

set "CHROME_EXE="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined CHROME_EXE if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined CHROME_EXE if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME_EXE=%LocalAppData%\Google\Chrome\Application\chrome.exe"

if not defined CHROME_EXE (
  for /f "tokens=2,*" %%A in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" /ve 2^>nul ^| findstr /i "REG_"') do (
    if exist "%%~B" set "CHROME_EXE=%%~B"
  )
)
if not defined CHROME_EXE (
  for /f "tokens=2,*" %%A in ('reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" /ve 2^>nul ^| findstr /i "REG_"') do (
    if exist "%%~B" set "CHROME_EXE=%%~B"
  )
)

if not defined CHROME_EXE (
  echo [ERROR] Could not locate chrome.exe via ProgramFiles, LocalAppData, or Windows Registry.
  exit /b 1
)

echo [WARNING] Remote debugging on 127.0.0.1:9333 exposes this logged-in TikTok profile to local processes on this machine. Close the browser when finished.
start "" "%CHROME_EXE%" --remote-debugging-address=127.0.0.1 --remote-debugging-port=9333 --user-data-dir="%CD%\tools\tiktok_browser_profile" --no-first-run "https://www.tiktok.com/login?redirect_url=https%%3A%%2F%%2Fwww.tiktok.com%%2Ftiktokstudio%%2Fupload"
