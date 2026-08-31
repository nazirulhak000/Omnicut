@echo off
title TikTok Auto-Cutter Pro Studio Launcher
echo ========================================================
echo   TikTok Auto-Cutter Pro Studio (Kill and Run)
echo ========================================================
echo.

echo [1/3] Terminating any existing servers on ports 8000, 5173, 8501...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8501" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [2/3] Launching FastAPI Backend on http://localhost:8000 ...
start "TikTok Auto-Cutter Backend (FastAPI)" cmd /k "python scripts/api_server.py"

echo [3/3] Launching React Vite Frontend on http://localhost:5173 ...
cd /d "%~dp0frontend"
start "TikTok Auto-Cutter Frontend (Vite)" cmd /k "npm run dev"

echo.
echo ========================================================
echo   System Started Successfully!
echo   Frontend URL: http://localhost:5173
echo   Backend API:  http://localhost:8000/docs
echo ========================================================
echo.
ping -n 3 127.0.0.1 >nul
start http://localhost:5173
