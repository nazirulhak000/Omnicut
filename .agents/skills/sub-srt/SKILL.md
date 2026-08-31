---
name: sub-srt
description: Generate accurate .srt (and .vtt) subtitles from an audio or video clip for CapCut and any editor, using real local speech recognition (never guessed timestamps). Default is bilingual stacked captions — the spoken line plus an English translation. Cross-platform (Apple-Silicon GPU via mlx-whisper, else faster-whisper). Use when the user wants subtitles/captions/SRT from a video or audio file (Thai / Chinese / English, incl. Thai+English mixed).
---

# sub-srt

Turn one audio/video file into a clean, timeline-accurate subtitle file for CapCut
(or Premiere / DaVinci / Final Cut). Cross-platform and shareable.

## Hard rule — never fake timestamps
Timestamps come **only** from the speech-recognition engine. Never hand-write,
estimate, or reconstruct timings from a transcript. Your job = run the engine and
let the script re-chunk its real timestamps.

## Run

```bash
~/.claude/skills/sub-srt/sub-srt "/path/to/clip.mp4" --lang th
```
- Video **or** audio in; audio auto-extracted.
- Default **bilingual** output → `clip-sub.srt` (spoken line + English translation stacked).
- Progress prints to stderr; the written path(s) print to stdout.

### Modes
Every caption box holds **~`--words-per-line` words (default 5), one short line per
language**. The original (Thai) is accurately time-synced; the English translation
is distributed **evenly across the boxes in speaking order** and snapped to clause
breaks — read the English lines top-to-bottom and they form the whole translation
(each box's English need not be a full sentence). Tuned to match natural CapCut-style
bilingual captions (~5 words original / ~4 English per box).
| `--mode` | Output file(s) |
|---|---|
| `bilingual` (default) | `clip-sub.srt` — original chunk + matching English chunk |
| `mono` | `clip-sub.srt` — single short-chunk track (no English) |
| `dual` | `clip-sub-<lang>.srt` + `clip-sub-en.srt` |

Change box size with `--words-per-line N` (e.g. `4` for bigger text, `6` for wider).
Note: bilingual timing is exact for the original; the English rides along in order,
not word-locked (matches how Gemini/LLM bilingual subs read).

### Language
- Default auto-detect. For a mostly-one-language clip **always pass `--lang`** — far
  more accurate. The common Thai+English case → use `--lang th` (Whisper keeps
  embedded English words in Latin script and translates the whole to English for the
  bottom line).
- **Limit:** Whisper locks one language per clip; truly code-switched Thai+Chinese+English
  is best-effort. Warn the user; suggest `--lang` or splitting the clip.

### Common options
`--model` (tiny·base·small·medium·large-v3·turbo, default large-v3) · `--fast` (turbo) ·
`--words-per-line 4` · `--chars-per-line` (zh/ja 8, th 14) · `--max-lines 2` ·
`--min-dur 1.0` · `--max-dur 6.0` · `--min-gap 80`(ms) · `--lead-out 1.0`
(extra seconds each caption lingers, capped at the next box — never overlaps) · `--pause-gap 0.6` ·
`--vtt` (also emit WebVTT) · `--bom` (UTF-8 BOM) · `--out` / `--outdir`.

## Output quality guarantees
Word-level re-chunk · cuts at pauses/sentence ends · enforced 1.0–6.0s on screen,
80 ms gap · strict SRT (1-based index, `HH:MM:SS,mmm`, **CRLF + UTF-8 no BOM**) →
renders Thai/Chinese and imports into every major NLE.

## Caption text pass — do this EVERY time, before delivering
The engine owns the **timestamps — never change those** (the hard rule stands). But the
engine's *text* is raw: it garbles words, splits mid-word, mis-translates, and leaves
spoken English untranslated. So after generating, do a quick **text-only** rewrite of the
caption lines (rebalance wording across adjacent boxes as needed; timings stay put). This
is what makes the FIRST output ship-ready — no second "fix the English" round.

1. **Sentences must make sense.** Every box reads as coherent Thai / English. Fix Whisper
   garbles, dropped syllables, and bad splits so each caption is understandable on its own.
2. **Keep one sentence's words together; no awkward seams between sentences.** Don't leave a
   box holding the tail of one sentence + the head of the next — snap box boundaries to
   sentence/clause ends. **Never break a word across boxes** (Thai included: respect
   pythainlp word tokens — e.g. never `มิ`/`น`; rejoin by shifting the boundary char).
3. **Double-check the English line** against the Thai meaning. Fix mistranslations
   (e.g. หมอดู = *fortune teller*, not "doctor"), keep brand/product names consistent
   (e.g. one spelling for "Go Check"), and fix scrambled word order or thin one-word boxes.
4. **Thai line: translate spoken English → Thai, except คำทับศัพท์.** When the speaker says
   English words/phrases, render them in Thai on the **top (Thai) line** — *except*
   transliterated loanwords and proper/brand/tech names, which stay as-is. The **English
   (bottom) line always stays English.**
   - **Translate** descriptive words + full spoken-English sentences → Thai:
     `support creativity` → `ส่งเสริมความคิดสร้างสรรค์`, `cozy` → `อบอุ่น`,
     `she won't be using it anyway` → `ยังไงก็ไม่ได้ใช้อยู่แล้ว`.
   - **Keep (คำทับศัพท์)** brands/products (CapCut, DJI, Notion, ClickUp, iPhone) and
     established loanwords (AI, app, online, section, sofa/โซฟา).

Keep recurring names consistent: if a person's or brand's name recurs, lock one spelling
and auto-correct Whisper's near-misses to it (while leaving real different words alone —
e.g. don't "correct" a month or a common noun that happens to look similar).

## Always report the post-check
Relay the script's `[5/5]` line: caption count, coverage vs audio length, and any
**⚠ FLAGS** (low coverage = wrong language / early stop; missing-English lines =
weak translation pass). Low coverage is the #1 tell that something is off.

## Engine / setup
Cross-platform, auto-detected: **mlx-whisper (GPU)** on Apple Silicon, **faster-whisper
(CPU/CUDA)** elsewhere. Isolated `.venv`, bundled ffmpeg via imageio-ffmpeg — no sudo.
If the venv is missing (fresh clone / shared copy), run `bash setup.sh`
(or `setup.ps1` on Windows) once. Shareable: distribute the folder WITHOUT `.venv`
(see `.gitignore`); the recipient runs setup. Full docs in `README.md`.
