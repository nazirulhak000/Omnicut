#!/bin/bash
# sub-srt setup — creates an isolated venv and installs the right Whisper engine
# for THIS machine. Safe: no sudo, no system Python changes, no Homebrew needed.
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null || { echo "Python 3 not found. Install Python 3.9+ first."; exit 1; }

echo "==> Creating venv at $VENV"
"$PY" -m venv "$VENV"
VPY="$VENV/bin/python"; [ -x "$VPY" ] || VPY="$VENV/Scripts/python.exe"
"$VPY" -m pip install --quiet --upgrade pip

OS="$(uname -s 2>/dev/null || echo unknown)"
ARCH="$(uname -m 2>/dev/null || echo unknown)"
echo "==> Detected: $OS / $ARCH"

echo "==> Installing bundled ffmpeg (imageio-ffmpeg)"
"$VPY" -m pip install --quiet imageio-ffmpeg

if [ "$OS" = "Darwin" ] && { [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; }; then
  echo "==> Apple Silicon: installing mlx-whisper (GPU)"
  "$VPY" -m pip install --quiet mlx-whisper
else
  echo "==> Installing faster-whisper (CPU; uses CUDA automatically if present)"
  "$VPY" -m pip install --quiet faster-whisper
fi

echo "==> Installing word segmenters for Thai/Chinese line breaks (pythainlp, jieba)"
"$VPY" -m pip install --quiet pythainlp jieba || \
  echo "   (optional segmenters failed — will fall back to grapheme wrapping)"

echo "==> Verifying"
"$VPY" - <<'PYEOF'
import importlib, imageio_ffmpeg
eng = "mlx-whisper" if importlib.util.find_spec("mlx_whisper") else \
      "faster-whisper" if importlib.util.find_spec("faster_whisper") else "NONE"
print("   engine:", eng)
print("   ffmpeg:", imageio_ffmpeg.get_ffmpeg_exe())
assert eng != "NONE", "no whisper engine installed"
print("   OK")
PYEOF

echo
echo "Done. Run captions with:"
echo "   \"$DIR/sub-srt\" /path/to/clip.mp4 --lang th"
echo "(first run downloads the model, ~1.5 GB for large-v3, then it's cached)"
