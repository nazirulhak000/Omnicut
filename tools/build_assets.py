"""
Master Asset Builder for OmniCut Pro Studio
Generates and populates all 7 asset categories in 02_Assets/ with professional quality.
"""

import os
import sys
import math
import wave
import struct
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ASSETS_DIR = PROJECT_ROOT / "02_Assets"
MUSIC_DIR = ASSETS_DIR / "Music"
SFX_DIR = ASSETS_DIR / "SFX"
FONTS_DIR = ASSETS_DIR / "Fonts"
STICKERS_DIR = ASSETS_DIR / "Stickers_Memes"
TEMPLATES_DIR = ASSETS_DIR / "Templates"
LUTS_DIR = ASSETS_DIR / "LUTs_ColorPresets"
VOICE_DIR = ASSETS_DIR / "Voiceover"

for d in [MUSIC_DIR, SFX_DIR, FONTS_DIR, STICKERS_DIR, TEMPLATES_DIR, LUTS_DIR, VOICE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# 1. AUDIO SYNTHESIS ENGINE (44.1kHz Stereo / Mono WAV)
# -----------------------------------------------------------------------------
SR = 44100

def write_wav(filename: Path, audio_data: np.ndarray, stereo: bool = True):
    """Writes float32 numpy array [-1.0, 1.0] to 16-bit PCM WAV."""
    audio_data = np.clip(audio_data, -0.99, 0.99)
    int_data = (audio_data * 32767).astype(np.int16)
    
    if stereo and int_data.ndim == 1:
        int_data = np.column_stack((int_data, int_data))
    
    num_channels = 2 if (stereo or (int_data.ndim > 1 and int_data.shape[1] == 2)) else 1
    
    with wave.open(str(filename), 'wb') as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(int_data.tobytes())

def generate_sfx_library():
    print("🔊 [1/5] Generating Sound Effects (SFX)...")
    
    # 1. Vine Boom / Deep Sub Impact (0.8s)
    t = np.linspace(0, 0.8, int(SR * 0.8), endpoint=False)
    freq = 90.0 * np.exp(-t * 5.0) # dropping frequency
    env = np.exp(-t * 4.0)
    sine = np.sin(2 * np.pi * freq * t)
    # Add punch distortion
    boom = np.tanh(sine * 2.5) * env * 0.95
    # Sub bass layer
    sub = np.sin(2 * np.pi * 45 * t) * np.exp(-t * 2.5) * 0.6
    write_wav(SFX_DIR / "sfx_vine_boom.wav", boom + sub)
    write_wav(SFX_DIR / "boom.wav", boom + sub) # legacy alias

    # 2. Sub Drop (1.2s)
    t = np.linspace(0, 1.2, int(SR * 1.2), endpoint=False)
    f_drop = 120.0 * np.exp(-t * 2.5)
    env = np.exp(-t * 1.8)
    sub_drop = np.sin(2 * np.pi * f_drop * t) * env * 0.9
    write_wav(SFX_DIR / "sfx_sub_drop.wav", sub_drop)

    # 3. Record Scratch (0.35s)
    t = np.linspace(0, 0.35, int(SR * 0.35), endpoint=False)
    noise = np.random.uniform(-1, 1, len(t))
    f_mod = 1200 + 800 * np.sin(2 * np.pi * 18 * t)
    scratch = np.sin(2 * np.pi * f_mod * t) * noise * np.exp(-t * 8.0) * 0.85
    write_wav(SFX_DIR / "sfx_record_scratch.wav", scratch)

    # 4. Camera Shutter (0.3s)
    t = np.linspace(0, 0.3, int(SR * 0.3), endpoint=False)
    click1 = np.sin(2 * np.pi * 2200 * t[:int(SR*0.05)]) * np.exp(-t[:int(SR*0.05)] * 60)
    click2 = np.sin(2 * np.pi * 1800 * t[:int(SR*0.06)]) * np.exp(-t[:int(SR*0.06)] * 50)
    shutter = np.zeros(len(t))
    shutter[:len(click1)] += click1 * 0.8
    shutter[int(SR*0.08):int(SR*0.08)+len(click2)] += click2 * 0.7
    write_wav(SFX_DIR / "sfx_camera_shutter.wav", shutter)

    # 5. Gasp / Shock Air (0.4s)
    t = np.linspace(0, 0.4, int(SR * 0.4), endpoint=False)
    air = np.random.normal(0, 0.3, len(t))
    env = np.sin(np.pi * t / 0.4) ** 2
    gasp = air * env * 0.7
    write_wav(SFX_DIR / "sfx_gasp_shock.wav", gasp)

    # 6. Whoosh Fast & Heavy (0.3s & 0.5s)
    t = np.linspace(0, 0.3, int(SR * 0.3), endpoint=False)
    noise = np.random.uniform(-0.5, 0.5, len(t))
    env = np.sin(np.pi * t / 0.3) ** 3
    whoosh_fast = noise * env * 0.9
    write_wav(SFX_DIR / "sfx_whoosh_fast.wav", whoosh_fast)
    write_wav(SFX_DIR / "whoosh.wav", whoosh_fast)

    t_h = np.linspace(0, 0.5, int(SR * 0.5), endpoint=False)
    noise_h = np.random.uniform(-0.6, 0.6, len(t_h))
    f_sweep = 300 + 600 * np.sin(np.pi * t_h / 0.5)
    sine_sweep = np.sin(2 * np.pi * f_sweep * t_h) * 0.3
    whoosh_heavy = (noise_h + sine_sweep) * (np.sin(np.pi * t_h / 0.5) ** 2) * 0.95
    write_wav(SFX_DIR / "sfx_whoosh_heavy.wav", whoosh_heavy)
    write_wav(SFX_DIR / "sfx_swoosh_air.wav", whoosh_fast * 0.7)
    write_wav(SFX_DIR / "sfx_whip_pan.wav", whoosh_fast * 1.1)

    # 7. Cartoon Pop / Bubble Pop (0.15s)
    t = np.linspace(0, 0.15, int(SR * 0.15), endpoint=False)
    freq_pop = 350 + 1200 * np.exp(-t * 40)
    pop = np.sin(2 * np.pi * freq_pop * t) * np.exp(-t * 30) * 0.9
    write_wav(SFX_DIR / "sfx_pop_bubble.wav", pop)
    write_wav(SFX_DIR / "pop.wav", pop)

    freq_cork = 250 + 800 * np.exp(-t * 25)
    pop_cork = np.sin(2 * np.pi * freq_cork * t) * np.exp(-t * 20) * 0.85
    write_wav(SFX_DIR / "sfx_pop_cork.wav", pop_cork)

    # 8. UI Clicks (Mouse, Keyboard, Lock) (0.05s)
    t = np.linspace(0, 0.06, int(SR * 0.06), endpoint=False)
    click = np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 120) * 0.8
    write_wav(SFX_DIR / "sfx_mouse_click.wav", click)
    write_wav(SFX_DIR / "sfx_keyboard_tap.wav", click * 0.7)
    
    t_l = np.linspace(0, 0.1, int(SR * 0.1), endpoint=False)
    lock = np.sin(2 * np.pi * 600 * t_l) * np.exp(-t_l * 50) + np.sin(2 * np.pi * 1400 * t_l) * np.exp(-t_l * 70) * 0.5
    write_wav(SFX_DIR / "sfx_iphone_lock.wav", lock * 0.85)

    # 9. Tactile / ASMR (Magnet Clack, Tear, Splash)
    t = np.linspace(0, 0.2, int(SR * 0.2), endpoint=False)
    metal = (np.sin(2 * np.pi * 850 * t) + np.sin(2 * np.pi * 2100 * t) * 0.5) * np.exp(-t * 35)
    thump = np.sin(2 * np.pi * 120 * t) * np.exp(-t * 25)
    clack = (metal + thump) * 0.9
    write_wav(SFX_DIR / "sfx_magnet_clack.wav", clack)

    t = np.linspace(0, 0.35, int(SR * 0.35), endpoint=False)
    tear_noise = np.random.uniform(-0.5, 0.5, len(t)) * (1.0 + np.sin(2 * np.pi * 40 * t))
    tear = tear_noise * np.exp(-t * 8) * 0.75
    write_wav(SFX_DIR / "sfx_unboxing_tear.wav", tear)

    t = np.linspace(0, 0.3, int(SR * 0.3), endpoint=False)
    splash_f = 600 + 400 * np.sin(2 * np.pi * 30 * t)
    splash = np.sin(2 * np.pi * splash_f * t) * np.random.uniform(0.5, 1.0, len(t)) * np.exp(-t * 12) * 0.7
    write_wav(SFX_DIR / "sfx_water_splash.wav", splash)

    # 10. Bell Ding & Magic Sparkle (0.6s & 0.8s)
    t = np.linspace(0, 0.8, int(SR * 0.8), endpoint=False)
    ding = (np.sin(2 * np.pi * 2093 * t) + 0.5 * np.sin(2 * np.pi * 4186 * t)) * np.exp(-t * 4.5) * 0.85
    write_wav(SFX_DIR / "sfx_bell_ding.wav", ding)
    write_wav(SFX_DIR / "ding.wav", ding)

    sparkle = np.zeros(len(t))
    sparkle_notes = [1568, 1760, 2093, 2349, 2793, 3136]
    for i, freq in enumerate(sparkle_notes):
        st_idx = int(i * 0.08 * SR)
        end_idx = min(len(t), st_idx + int(0.3 * SR))
        sub_t = np.linspace(0, (end_idx - st_idx)/SR, end_idx - st_idx)
        sparkle[st_idx:end_idx] += np.sin(2 * np.pi * freq * sub_t) * np.exp(-sub_t * 8) * 0.25
    write_wav(SFX_DIR / "sfx_magic_sparkle.wav", sparkle)

    # 11. Tada Fanfare (0.9s)
    t_fanfare = np.linspace(0, 0.9, int(SR * 0.9), endpoint=False)
    fanfare = np.zeros(len(t_fanfare))
    chords = [
        (0.00, 0.15, [523.25, 659.25]), # C5, E5
        (0.16, 0.30, [659.25, 783.99]), # E5, G5
        (0.32, 0.85, [523.25, 659.25, 783.99, 1046.50]) # C Major Fanfare
    ]
    for st_s, end_s, freqs in chords:
        st_idx = int(st_s * SR)
        end_idx = min(len(t_fanfare), int(end_s * SR))
        sub_t = np.linspace(0, (end_idx - st_idx)/SR, end_idx - st_idx)
        for f in freqs:
            fanfare[st_idx:end_idx] += (np.sin(2 * np.pi * f * sub_t) + 0.3 * np.sin(2 * np.pi * f * 2 * sub_t)) * np.exp(-sub_t * 3.5) * 0.2
    write_wav(SFX_DIR / "sfx_tada_fanfare.wav", fanfare)

    # 12. Cash Register & Coins (0.7s)
    t = np.linspace(0, 0.7, int(SR * 0.7), endpoint=False)
    bell1 = np.sin(2 * np.pi * 2489 * t[:int(SR*0.25)]) * np.exp(-t[:int(SR*0.25)] * 10)
    bell2 = np.sin(2 * np.pi * 3136 * t[:int(SR*0.35)]) * np.exp(-t[:int(SR*0.35)] * 8)
    drawer = np.random.uniform(-0.3, 0.3, int(SR*0.25)) * np.exp(-np.linspace(0, 0.25, int(SR*0.25)) * 12)
    cash = np.zeros(len(t))
    cash[:len(bell1)] += bell1 * 0.6
    cash[int(SR*0.08):int(SR*0.08)+len(bell2)] += bell2 * 0.7
    cash[int(SR*0.12):int(SR*0.12)+len(drawer)] += drawer * 0.5
    write_wav(SFX_DIR / "sfx_cash_register.wav", cash)
    write_wav(SFX_DIR / "cash.wav", cash)

    # Coin drop
    t_coin = np.linspace(0, 0.4, int(SR * 0.4), endpoint=False)
    coin = (np.sin(2 * np.pi * 3520 * t_coin) + 0.6 * np.sin(2 * np.pi * 4400 * t_coin)) * np.exp(-t_coin * 12) * 0.8
    write_wav(SFX_DIR / "sfx_coin_drop.wav", coin)

    # Notification bell
    t_notif = np.linspace(0, 0.45, int(SR * 0.45), endpoint=False)
    n1 = np.sin(2 * np.pi * 1318.5 * t_notif[:int(SR*0.2)]) * np.exp(-t_notif[:int(SR*0.2)] * 12) # E6
    n2 = np.sin(2 * np.pi * 1760.0 * t_notif[:int(SR*0.3)]) * np.exp(-t_notif[:int(SR*0.3)] * 8)  # A6
    notif = np.zeros(len(t_notif))
    notif[:len(n1)] += n1 * 0.5
    notif[int(SR*0.1):int(SR*0.1)+len(n2)] += n2 * 0.65
    write_wav(SFX_DIR / "sfx_bell_notification.wav", notif)
    print(f"   ✓ Generated 22+ SFX files in {SFX_DIR}")

def generate_music_library():
    print("🎵 [2/5] Generating Background Music Loops (BGM)...")
    
    # Helper to generate musical drum beat + bassline loop (30s)
    def create_loop(bpm: float, duration_s: float = 30.0, genre: str = "funk"):
        total_samples = int(SR * duration_s)
        t = np.linspace(0, duration_s, total_samples, endpoint=False)
        track = np.zeros(total_samples, dtype=np.float32)
        
        beat_dur = 60.0 / bpm
        bar_dur = beat_dur * 4
        num_bars = int(duration_s / bar_dur)
        
        # Bass kick pattern (4 on the floor or syncopated)
        for b in range(int(duration_s / beat_dur)):
            st_idx = int(b * beat_dur * SR)
            dur_k = int(0.12 * SR)
            if st_idx + dur_k < total_samples:
                tk = np.linspace(0, 0.12, dur_k)
                kick = np.sin(2 * np.pi * (130 * np.exp(-tk * 25)) * tk) * np.exp(-tk * 20) * 0.65
                track[st_idx:st_idx+dur_k] += kick

        # Snare / Clap on beats 2 & 4
        for b in range(int(duration_s / beat_dur)):
            if b % 2 == 1: # 2nd and 4th beats
                st_idx = int(b * beat_dur * SR)
                dur_s = int(0.15 * SR)
                if st_idx + dur_s < total_samples:
                    ts = np.linspace(0, 0.15, dur_s)
                    snare = np.random.uniform(-0.4, 0.4, dur_s) * np.exp(-ts * 18)
                    track[st_idx:st_idx+dur_s] += snare

        # Hi-hat on 8th notes
        for b in range(int(duration_s / (beat_dur / 2))):
            st_idx = int(b * (beat_dur / 2) * SR)
            dur_h = int(0.04 * SR)
            if st_idx + dur_h < total_samples:
                th = np.linspace(0, 0.04, dur_h)
                hat = np.random.uniform(-0.15, 0.15, dur_h) * np.exp(-th * 80)
                track[st_idx:st_idx+dur_h] += hat

        # Melodic Chords & Bassline based on genre
        if genre == "funk": # Upbeat Brass Funk (125 BPM)
            scale = [220, 261.63, 293.66, 329.63, 392.00] # A Minor Pentatonic
            for bar in range(num_bars):
                for i, freq in enumerate(scale):
                    st_idx = int((bar * bar_dur + i * (beat_dur * 0.75)) * SR)
                    dur_n = int(beat_dur * 0.6 * SR)
                    if st_idx + dur_n < total_samples:
                        tn = np.linspace(0, beat_dur * 0.6, dur_n)
                        brass = (np.sin(2 * np.pi * freq * tn) + 0.5 * np.sin(2 * np.pi * freq * 2 * tn) + 0.2 * np.sin(2 * np.pi * freq * 3 * tn)) * np.exp(-tn * 4) * 0.25
                        track[st_idx:st_idx+dur_n] += brass

        elif genre == "cozy": # Acoustic Whistle & Ukulele (108 BPM)
            scale = [261.63, 329.63, 392.00, 523.25] # C Major
            for bar in range(num_bars):
                for i, freq in enumerate(scale):
                    st_idx = int((bar * bar_dur + i * beat_dur) * SR)
                    dur_n = int(beat_dur * 0.9 * SR)
                    if st_idx + dur_n < total_samples:
                        tn = np.linspace(0, beat_dur * 0.9, dur_n)
                        acoustic = np.sin(2 * np.pi * freq * tn) * np.exp(-tn * 2.5) * 0.2
                        track[st_idx:st_idx+dur_n] += acoustic

        elif genre == "phonk": # 808 Phonk Bass (135 BPM)
            cowbell = [587.33, 659.25, 783.99, 880.00] # D, E, G, A
            for bar in range(num_bars):
                for i, freq in enumerate(cowbell):
                    st_idx = int((bar * bar_dur + i * (beat_dur * 0.5)) * SR)
                    dur_n = int(0.18 * SR)
                    if st_idx + dur_n < total_samples:
                        tn = np.linspace(0, 0.18, dur_n)
                        bell = np.sin(2 * np.pi * freq * tn) * np.exp(-tn * 15) * 0.35
                        track[st_idx:st_idx+dur_n] += bell

        elif genre == "pop": # Korean Aesthetic Pop (115 BPM)
            chords = [523.25, 587.33, 659.25, 698.46] # C, D, E, F
            for bar in range(num_bars):
                for i, freq in enumerate(chords):
                    st_idx = int((bar * bar_dur + i * beat_dur) * SR)
                    dur_n = int(beat_dur * 0.8 * SR)
                    if st_idx + dur_n < total_samples:
                        tn = np.linspace(0, beat_dur * 0.8, dur_n)
                        rhodes = (np.sin(2 * np.pi * freq * tn) + 0.3 * np.sin(2 * np.pi * freq * 1.5 * tn)) * np.exp(-tn * 2.0) * 0.22
                        track[st_idx:st_idx+dur_n] += rhodes

        elif genre == "urgent": # Flash Sale Countdown Trap (140 BPM)
            # Ticking clock
            for b in range(int(duration_s / (beat_dur / 4))):
                st_idx = int(b * (beat_dur / 4) * SR)
                dur_t = int(0.02 * SR)
                if st_idx + dur_t < total_samples:
                    tt = np.linspace(0, 0.02, dur_t)
                    tick = np.sin(2 * np.pi * 3800 * tt) * np.exp(-tt * 150) * 0.2
                    track[st_idx:st_idx+dur_t] += tick

        return track

    write_wav(MUSIC_DIR / "bgm_brass_funk.wav", create_loop(125, 35.0, "funk"))
    write_wav(MUSIC_DIR / "tiktok_upbeat_bgm.wav", create_loop(125, 35.0, "funk")) # default alias
    write_wav(MUSIC_DIR / "bgm_whistle_cozy.wav", create_loop(108, 35.0, "cozy"))
    write_wav(MUSIC_DIR / "bgm_cyber_phonk.wav", create_loop(135, 35.0, "phonk"))
    write_wav(MUSIC_DIR / "bgm_aesthetic_pop.wav", create_loop(115, 35.0, "pop"))
    write_wav(MUSIC_DIR / "bgm_flash_sale_urgent.wav", create_loop(140, 35.0, "urgent"))
    write_wav(MUSIC_DIR / "bgm_lofi_daily.wav", create_loop(90, 35.0, "cozy"))
    print(f"   ✓ Generated 6 BGM Tracks in {MUSIC_DIR}")

# -----------------------------------------------------------------------------
# 2. GRAPHIC OVERLAYS & STICKERS GENERATOR (RGBA PNG)
#
# SUPERSEDED for the sticker/badge output -- 02_Assets/Stickers_Memes/ on
# disk today holds the 8 badge_*_3d.png files from build_3d_pro_badges.py
# (the canonical generator), not this function's filenames. Re-running the
# full build_assets.py pipeline would drop a second, mismatched sticker set
# that the render pipeline does not reference. The banner/frame template
# outputs into Templates/ are still current and fine to regenerate.
# -----------------------------------------------------------------------------
def generate_stickers_and_templates():
    print("🏷️ [3/5] Generating Stickers & Banners (PNG Overlays)...")

    def get_font(size: int = 48, bold: bool = True):
        font_path = FONTS_DIR / ("Kanit-Black.ttf" if bold else "Kanit-ExtraBold.ttf")
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size)
        return ImageFont.load_default()

    # 1. Yellow Basket Arrow (TikTok Shop Call-To-Action) (400x400)
    img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw curved arrow pointing bottom-left
    # Tail to head
    points = [(320, 80), (280, 220), (140, 280)]
    draw.line(points, fill=(255, 230, 0, 255), width=28, joint="curve")
    # Arrow head
    draw.polygon([(80, 320), (160, 240), (170, 310)], fill=(255, 230, 0, 255))
    # Text on arrow "จิ้มตะกร้าซ้ายล่าง"
    font_sm = get_font(28)
    draw.text((160, 110), "กดตะกร้า 👇", fill=(0, 0, 0, 255), font=font_sm, stroke_width=4, stroke_fill=(255, 230, 0, 255))
    img.save(STICKERS_DIR / "sticker_yellow_basket_arrow.png", "PNG")

    # 2. Flash Sale Red Badge (380x140)
    img = Image.new("RGBA", (380, 140), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Rounded badge
    draw.rounded_rectangle([(10, 10), (370, 130)], radius=24, fill=(254, 44, 85, 255), outline=(255, 255, 255, 255), width=4)
    font_sale = get_font(38)
    draw.text((45, 45), "⚡ FLASH SALE", fill=(255, 255, 255, 255), font=font_sale, stroke_width=3, stroke_fill=(0, 0, 0, 255))
    img.save(STICKERS_DIR / "badge_flash_sale_red.png", "PNG")

    # 3. 50% Discount Badge (240x240 circle)
    img = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([(10, 10), (230, 230)], fill=(255, 102, 0, 255), outline=(255, 255, 255, 255), width=5)
    font_disc = get_font(38)
    draw.text((45, 60), "ลดพิเศษ", fill=(255, 255, 255, 255), font=get_font(28))
    draw.text((60, 105), "-50%", fill=(255, 230, 0, 255), font=font_disc, stroke_width=2, stroke_fill=(0,0,0,255))
    img.save(STICKERS_DIR / "badge_discount_50.png", "PNG")

    # 4. 1 แถม 1 Badge (260x120)
    img = Image.new("RGBA", (260, 120), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(10, 10), (250, 110)], radius=20, fill=(147, 51, 234, 255), outline=(255, 230, 0, 255), width=4)
    draw.text((35, 35), "🔥 1 แถม 1", fill=(255, 255, 255, 255), font=get_font(36), stroke_width=2, stroke_fill=(0,0,0,255))
    img.save(STICKERS_DIR / "badge_buy1_get1.png", "PNG")

    # 5. Free Shipping Badge (300x110)
    img = Image.new("RGBA", (300, 110), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(10, 10), (290, 100)], radius=18, fill=(16, 185, 129, 255), outline=(255, 255, 255, 255), width=3)
    draw.text((30, 32), "🚚 ส่งฟรีทั่วไทย", fill=(255, 255, 255, 255), font=get_font(32), stroke_width=2, stroke_fill=(0,0,0,255))
    img.save(STICKERS_DIR / "badge_free_shipping.png", "PNG")

    # 6. 5 Stars Rating Badge (420x110)
    img = Image.new("RGBA", (420, 110), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(10, 10), (410, 100)], radius=16, fill=(15, 23, 42, 230), outline=(255, 215, 0, 255), width=2)
    draw.text((30, 25), "⭐️⭐️⭐️⭐️⭐️ (10k+ รีวิว)", fill=(255, 215, 0, 255), font=get_font(28))
    draw.text((32, 60), "การันตียอดขายอันดับ 1", fill=(255, 255, 255, 255), font=get_font(20))
    img.save(STICKERS_DIR / "rating_5_stars.png", "PNG")

    # 7. Check & Cross Icons (140x140)
    img_chk = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
    d_chk = ImageDraw.Draw(img_chk)
    d_chk.ellipse([(10, 10), (130, 130)], fill=(16, 185, 129, 255), outline=(255, 255, 255, 255), width=4)
    d_chk.line([(40, 70), (65, 95), (105, 45)], fill=(255, 255, 255, 255), width=10)
    img_chk.save(STICKERS_DIR / "icon_check_green.png", "PNG")

    img_crs = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
    d_crs = ImageDraw.Draw(img_crs)
    d_crs.ellipse([(10, 10), (130, 130)], fill=(239, 68, 68, 255), outline=(255, 255, 255, 255), width=4)
    d_crs.line([(45, 45), (95, 95)], fill=(255, 255, 255, 255), width=10)
    d_crs.line([(95, 45), (45, 95)], fill=(255, 255, 255, 255), width=10)
    img_crs.save(STICKERS_DIR / "icon_cross_red.png", "PNG")

    # 8. Banners: Neon Yellow & Urgent Red & Glass (1080x160)
    # Neon Yellow Header
    img_ny = Image.new("RGBA", (1080, 160), (0, 0, 0, 0))
    d_ny = ImageDraw.Draw(img_ny)
    d_ny.rectangle([(0, 0), (1080, 160)], fill=(255, 230, 0, 240))
    d_ny.line([(0, 155), (1080, 155)], fill=(0, 0, 0, 255), width=6)
    img_ny.save(TEMPLATES_DIR / "banner_hook_neon_yellow.png", "PNG")

    # Urgent Red Header
    img_rd = Image.new("RGBA", (1080, 160), (0, 0, 0, 0))
    d_rd = ImageDraw.Draw(img_rd)
    d_rd.rectangle([(0, 0), (1080, 160)], fill=(254, 44, 85, 245))
    d_rd.line([(0, 155), (1080, 155)], fill=(255, 255, 255, 255), width=4)
    img_rd.save(TEMPLATES_DIR / "banner_hook_urgent_red.png", "PNG")

    # Split Before/After Frame (1080x1920 with middle divider)
    img_spl = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d_spl = ImageDraw.Draw(img_spl)
    d_spl.line([(540, 0), (540, 1920)], fill=(255, 255, 255, 220), width=6)
    # VS Badge in center
    d_spl.ellipse([(470, 900), (610, 1040)], fill=(254, 44, 85, 255), outline=(255, 255, 255, 255), width=4)
    d_spl.text((505, 935), "VS", fill=(255, 255, 255, 255), font=get_font(44))
    img_spl.save(TEMPLATES_DIR / "frame_before_after_split.png", "PNG")
    print(f"   ✓ Generated transparent PNG stickers and templates in {STICKERS_DIR} and {TEMPLATES_DIR}")

# -----------------------------------------------------------------------------
# 3. COLOR GRADING LUTS (.cube)
# -----------------------------------------------------------------------------
def generate_lut_library():
    print("🎨 [4/5] Generating Color Grading LUTs (.cube)...")
    
    def write_cube(filename: Path, title: str, r_mult: float, g_mult: float, b_mult: float, gamma: float = 1.0):
        size = 17
        lines = [
            f'TITLE "{title}"',
            f'LUT_3D_SIZE {size}',
            'DOMAIN_MIN 0.0 0.0 0.0',
            'DOMAIN_MAX 1.0 1.0 1.0',
        ]
        for b in range(size):
            for g in range(size):
                for r in range(size):
                    rf = (r / (size - 1)) ** gamma * r_mult
                    gf = (g / (size - 1)) ** gamma * g_mult
                    bf = (b / (size - 1)) ** gamma * b_mult
                    lines.append(f"{min(1.0, rf):.6f} {min(1.0, gf):.6f} {min(1.0, bf):.6f}")
        
        filename.write_text("\n".join(lines), encoding="utf-8")

    write_cube(LUTS_DIR / "lut_bright_clean_product.cube", "Bright Clean Product", 1.08, 1.06, 1.04, gamma=0.92)
    write_cube(LUTS_DIR / "lut_tech_cool_contrast.cube", "Tech Cool Contrast", 0.98, 1.02, 1.10, gamma=0.88)
    write_cube(LUTS_DIR / "lut_warm_cozy_lifestyle.cube", "Warm Cozy Lifestyle", 1.10, 1.04, 0.94, gamma=0.95)
    write_cube(LUTS_DIR / "lut_vibrant_beauty_skin.cube", "Vibrant Beauty Skin", 1.08, 1.02, 1.05, gamma=0.90)
    print(f"   ✓ Generated 4 3D LUTs in {LUTS_DIR}")

# -----------------------------------------------------------------------------
# 4. VOICEOVER REFERENCE PRESETS
# -----------------------------------------------------------------------------
def generate_voiceover_presets():
    print("🎙️ [5/5] Generating Voiceover Reference Presets...")
    from scripts.voice_engine import VoiceEngine

    presets = [
        ("voice_preset_male_hype", "สวัสดีครับทุกคน วันนี้ใครกำลังหาสายชาร์จเร็ว แม่เหล็กแน่นๆ ต้องดูตัวนี้เลยครับ!", "male", 1.25),
        ("voice_preset_female_bright", "ทุกคนดูนี่สิคะ ตัวนี้ใช้ดีมาก ดีไซน์สวย มินิมอล เข้ากับทุกการใช้งานเลยค่ะ", "female", 1.20),
        ("voice_preset_pro_reviewer", "สวัสดีครับ สำหรับรุ่นนี้ผ่านการทดสอบมาตรฐาน ชาร์จไว ปลอดภัย ไม่ทำร้ายแบตเตอรี่ครับ", "male", 1.15)
    ]

    for name, text, gender, speed in presets:
        audio_file = VOICE_DIR / f"{name}.wav"
        txt_file = VOICE_DIR / f"{name}.txt"
        
        txt_file.write_text(text, encoding="utf-8")
        try:
            VoiceEngine.generate_crystal_voice(
                text_or_lines=text,
                output_audio_path=str(audio_file),
                speed=speed,
                voice_gender=gender
            )
        except Exception as e:
            print(f"   Notice: Voice generation fallback for {name}: {e}")

    print(f"   ✓ Generated Voiceover Presets in {VOICE_DIR}")

if __name__ == "__main__":
    print("\n=======================================================")
    print("🚀 BUILDING MASTER ASSET REPOSITORY")
    print("=======================================================\n")
    generate_sfx_library()
    generate_music_library()
    generate_stickers_and_templates()
    generate_lut_library()
    generate_voiceover_presets()
    print("\n🎉 ALL ASSET INVENTORIES COMPLETED SUCCESSFULLY!\n")
