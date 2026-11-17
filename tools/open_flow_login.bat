@echo off
setlocal EnableDelayedExpansion
title OmniCut - Google Flow Login

echo ==================================================================
echo   OmniCut Pro Studio - Google Flow Account Setup
echo ==================================================================
echo.

set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

if not exist "%CHROME%" (
    echo [ERROR] Google Chrome was not found on your system.
    echo Please install Google Chrome or specify its location.
    pause
    exit /b 1
)

set "PROFILE=%USERPROFILE%\.flow-mcp\chrome-profile"
set "TARGET_URL=https://accounts.google.com/AddSession?continue=https%%3A%%2F%%2Fflow.google.com%%2F"

echo Profile Directory: %PROFILE%
echo Target URL:        %TARGET_URL%
echo.
echo Launching Google Chrome...

start "" "%CHROME%" --user-data-dir="%PROFILE%" --remote-debugging-port=9333 "%TARGET_URL%"

echo.
echo ==================================================================
echo [OK] Chrome has been opened.
echo.
echo Instructions:
echo  1. In the Chrome window, sign in to your Google Pro account(s).
echo  2. To add account 2, 3, 4, 5: click your profile icon in Chrome
echo     and select "Add another account".
echo  3. When finished, return to OmniCut and click "Refresh" button.
echo ==================================================================
echo.
pause
