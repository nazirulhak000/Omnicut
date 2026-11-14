@echo off
rem Double-click to open Chrome for Google Flow one-time login.
cd /d "%~dp0"
chcp 65001 >nul
if not exist dist call npm run build
node dist\login.js
pause
