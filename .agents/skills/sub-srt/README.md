# sub-srt

Turn any audio/video clip into an **accurate** `.srt` subtitle file for CapCut,
Premiere, DaVinci Resolve, Final Cut, or any editor — with subtitles that are
**actually in sync**.

Timestamps come from real local speech recognition (Whisper), never guessed.
Great for Thai / Chinese / English short-form vertical video.

## Why it's better than the usual auto-caption tools
- **Real word-level timing** re-chunked into clean cues — no drift, no captions
  that flash by or linger.
- **~5 words per caption box** by default — big, readable text for vertical video.
- Word-accurate chunking for **Thai/Chinese** (pythainlp / jieba) — never mid-word.
- **Bilingual**: accurately-timed original + English distributed evenly in speaking
  order (snapped to clause breaks) — read the English lines in sequence = the full
  translation. Reads like clean LLM/Gemini bilingual subs, but the original is synced.
- **Deterministic & repetition-resistant** decoding — no hallucinated loops.
- Strict, universal SRT: 1-based index, `HH:MM:SS,mmm`, **CRLF + UTF-8**.
- Runs **fully local** — no upload, no per-minute fees, no watermark.

## Install (one time)

**Requirements:** Python 3.9+ installed. That's it — no admin/sudo, no Homebrew.

**macOS / Linux**
```bash
bash setup.sh
```
**Windows (PowerShell)**
```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

The setup script builds an isolated `.venv` and installs the right engine for your
machine automatically:
| Hardware | Engine | Uses |
|---|---|---|
| Apple Silicon (M-series) | `mlx-whisper` | GPU / Metal |
| Windows / Intel / Linux | `faster-whisper` | CPU (or NVIDIA CUDA if present) |

First caption run downloads the model (~1.5 GB for `large-v3`), then it's cached.

## Use

```bash
# macOS/Linux
./sub-srt "clip.mp4" --lang th
# Windows
.\.venv\Scripts\python.exe generate_srt.py "clip.mp4" --lang th
```

Output lands next to the source as `clip-sub.srt`. Drag it into your editor's
timeline / subtitle track.

### Modes
| `--mode` | Output |
|---|---|
| `bilingual` *(default)* | spoken line **+ English translation** stacked, one file |
| `mono` | single track, 3–4 words/line karaoke style |
| `dual` | two files: `clip-sub-th.srt` + `clip-sub-en.srt` |

### Key options
| Flag | Default | Meaning |
|------|---------|---------|
| `--lang` | auto | force source language (`th`/`zh`/`en`…). **Use it** for mostly-one-language clips |
| `--model` | `large-v3` | `tiny·base·small·medium·large-v3·turbo` or an hf repo id |
| `--fast` | off | draft speed (`turbo` model) |
| `--words-per-line` | `4` | words/line for spaced languages |
| `--chars-per-line` | zh/ja 8, th 14 | chars/line for CJK/Thai |
| `--min-dur` / `--max-dur` | `1.0` / `6.0` | seconds on screen |
| `--min-gap` | `80` | ms between captions |
| `--lead-out` | `1.0` | extra seconds each caption lingers, capped at the next box (never overlaps) |
| `--vtt` | off | also write a `.vtt` |
| `--bom` | off | add UTF-8 BOM (a few older Windows tools want it) |
| `--out` / `--outdir` | next to source | override output location |

## Known limitation
Whisper detects **one language per clip**. A clip that rapidly code-switches
(e.g. Thai + Chinese + English in one breath) will nail the dominant language and
approximate the rest. For those, pass `--lang` for the main language, or split the
clip. Straight Thai-with-some-English works well (pass `--lang th`).

## Uninstall
Delete this folder. Model cache lives in `~/.cache/huggingface` (delete to reclaim space).

---
MIT-style: use it, share it, remix it. Built as a Claude Code skill.
