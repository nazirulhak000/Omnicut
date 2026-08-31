# sub-srt setup for Windows (PowerShell). No admin rights needed.
# Usage:  powershell -ExecutionPolicy Bypass -File setup.ps1
$ErrorActionPreference = "Stop"
$DIR  = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV = Join-Path $DIR ".venv"

$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) { $py = (Get-Command python3 -ErrorAction SilentlyContinue) }
if (-not $py) { throw "Python 3.9+ not found. Install from python.org first." }

Write-Host "==> Creating venv at $VENV"
& $py.Source -m venv $VENV
$VPY = Join-Path $VENV "Scripts\python.exe"
& $VPY -m pip install --quiet --upgrade pip

Write-Host "==> Installing faster-whisper + bundled ffmpeg + Thai/Chinese segmenters"
& $VPY -m pip install --quiet faster-whisper imageio-ffmpeg pythainlp jieba

Write-Host "==> Verifying"
& $VPY -c "import faster_whisper, imageio_ffmpeg; print('   engine: faster-whisper'); print('   ffmpeg:', imageio_ffmpeg.get_ffmpeg_exe()); print('   OK')"

Write-Host ""
Write-Host "Done. Run:  & '$VENV\Scripts\python.exe' '$DIR\generate_srt.py' C:\path\to\clip.mp4 --lang th"
