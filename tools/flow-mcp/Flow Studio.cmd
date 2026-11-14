@echo off
rem Double-click to start the Flow Studio panel on Windows. Close this window to stop it.
cd /d "%~dp0"
chcp 65001 >nul
if not exist node_modules call npm install
if not exist dist call npm run build
node dist\studio.js
pause
