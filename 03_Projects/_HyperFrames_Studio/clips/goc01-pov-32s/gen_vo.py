"""Generate dual-character POV Couple voiceover using Gemini Flash TTS multiSpeakerVoiceConfig
(Kore = น้องน้ำพริก สาวใต้ปากแซ่บ, Puck = พี่บ่าว นายซื่อบื้อ) and transcribe exact word timestamps
with faster-whisper.
"""
import base64
import json
import subprocess
import sys
import urllib.request
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent.parent
OMNICUT_ROOT = STUDIO.parent.parent
sys.path.insert(0, str(OMNICUT_ROOT))

from scripts.config import get_gemini_api_keys  # noqa: E402

OUT_VO = STUDIO / "assets" / "clips" / "goc01-pov-32s" / "vo.wav"
OUT_VO.parent.mkdir(parents=True, exist_ok=True)

SCRIPT_PROMPT = """[Scene: Viral TikTok Sitcom Couple POV in Thailand.
Characters:
- Namphrik (Female, cute but fiery Southern Thai girlfriend, scolding fast, spicy, expressive, tsundere)
- Phibao (Male, clumsy, flustered, panicking boyfriend trying to make excuses, playful and comedic)
Pacing: Snappy, fast-paced, natural sitcom banter, high energy, ~30 seconds total.]

Read the following Thai dialogue with expressive acting:

Namphrik: พี่บ่าว! มานั่งตรงนี้เดี๋ยวนี้! เมื่อกี้เดินไปหลังบ้าน แหลงไหรไว้!
Phibao: ฮะ เปล่าครับที่รัก เค้าเดินไปเปิดพัดลมเฉยๆ ไม่ได้พูดอะไรเลย!
Namphrik: ไม่ได้แหลงบ้านมึงสิ! ฟังนะ ชัดระดับล้านเค!
Phibao: เมียดุยังกะหมาพิตบูล ตัวก็เล็กนิดเดียว ด่าทีบ้านสะเทือน
Namphrik: หมาพิตบูลพร่องมึงสิ! เปิดพัดลมเบอร์สาม เสียงลมไม่เข้าสักแอะ แต่เสียงนินทากูชัดยังกะมานอนแหลงในรูหู เบอะบะจริงนิ!
Phibao: โถ่ที่รัก ก็ใครจะคิดว่าไมค์ GoChek Ultra S24 ตัวแค่นี้ มันจะตัดเสียงลมเกลี้ยงเก้าสิบเปอร์เซ็นต์ล่ะ!
Namphrik: ไหนเอามาแลดิ๊ โห เคสชาร์จโคตรเท่ แบตอึดสามสิบห้าชั่วโมง แถมดูดเสียงทะลุกำแพงอีก ยึด!
Namphrik: ทีหลังไปเดินห้าง กูจะติดเสื้อมึงไว้ตลอด ได้แรงอก!
Phibao: จบกันชีวิตผม ใครอยากได้ไมค์ชัดทะลุกำแพง กดตะกร้าเหลืองซ้ายล่างเลยครับ
"""


def generate_multi_speaker_vo():
    api_keys = get_gemini_api_keys()
    if not api_keys:
        raise RuntimeError("No GEMINI_API_KEY found!")

    payload = {
        "contents": [{"parts": [{"text": SCRIPT_PROMPT}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "multiSpeakerVoiceConfig": {
                    "speakerVoiceConfigs": [
                        {
                            "speaker": "Namphrik",
                            "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}
                        },
                        {
                            "speaker": "Phibao",
                            "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Puck"}}
                        }
                    ]
                }
            }
        }
    }

    models = ["gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"]
    data = None
    for model_name in models:
        for idx, key in enumerate(api_keys, 1):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    print(f"Success with {model_name} on Key #{idx}")
                    break
            except Exception as e:
                print(f"Attempt {model_name} Key #{idx} failed: {e}")
        if data:
            break

    if not data:
        raise RuntimeError("All Gemini TTS attempts failed!")

    b64_audio = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    pcm_bytes = base64.b64decode(b64_audio)

    raw_wav = HERE / "raw_gemini_vo.wav"
    with wave.open(str(raw_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(pcm_bytes)

    # Speed up slightly (1.12x) and normalize to crisp broadcast -16 LUFS at 48kHz stereo
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_wav),
        "-af", "atempo=1.12,silenceremove=start_periods=1:start_duration=0.02:start_threshold=-42dB:stop_periods=-1:stop_duration=0.28:stop_threshold=-42dB,loudnorm=I=-16:TP=-1.5:LRA=9",
        "-ar", "48000", "-ac", "2", str(OUT_VO)
    ], check=True, capture_output=True)

    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(OUT_VO)
    ], check=True, capture_output=True, text=True)
    dur = round(float(probe.stdout.strip()), 3)
    (HERE / "vo_meta.json").write_text(json.dumps({"duration": dur}, indent=2), encoding="utf-8")
    print(f"Saved {OUT_VO} (duration: {dur}s)")
    return dur


def transcribe_vo():
    from faster_whisper import WhisperModel
    print("Running faster-whisper word-level transcription...")
    model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        str(OUT_VO),
        language="th",
        word_timestamps=True,
        initial_prompt="พี่บ่าว แหลงไหรไว้ พัดลม หมาพิตบูล เบอะบะจริงนิ GoChek Ultra S24 แลดิ๊ เคสชาร์จ ยึด ได้แรงอก ตะกร้าเหลืองซ้ายล่าง"
    )
    words = []
    for seg in segments:
        for w in (seg.words or []):
            txt = w.word.strip()
            if txt:
                words.append({"w": txt, "s": round(w.start, 3), "e": round(w.end, 3)})
    out_json = HERE / "whisper_words.json"
    out_json.write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Transcribed {len(words)} words to {out_json}")
    full_txt = "".join(w["w"] for w in words)
    print("Full transcript:", full_txt)


if __name__ == "__main__":
    if not OUT_VO.exists():
        generate_multi_speaker_vo()
    transcribe_vo()
