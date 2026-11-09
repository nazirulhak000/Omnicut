@echo off
setlocal
cd /d "%~dp0\.."
rem Unattended TikTok auto-post (one clip at a time). Examples:
rem   tools\start_autopost.bat --health
rem   tools\start_autopost.bat --dry-run --limit 3
rem   tools\start_autopost.bat --limit 10
node tools\autopost_conductor\run.js %*
exit /b %errorlevel%
