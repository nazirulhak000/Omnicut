@echo off
chcp 65001 >nul
title TikTok Sharpness Enhancer (OmniCut)

if "%~1"=="" (
    echo [OmniCut TikTok Sharpness Enhancer]
    echo.
    echo ลากไฟล์วิดีโอ .mp4 มาวางทับไฟล์นี้เพื่อเพิ่มความคมชัดสำหรับ TikTok ได้เลยครับ!
    echo.
    pause
    exit /b
)

python "%~dp0tiktok_enhancer.py" %*

echo.
echo =======================================================
echo เสร็จสิ้นเรียบร้อย! กดปุ่มใดก็ได้เพื่อปิดหน้านี้...
echo =======================================================
pause >nul
