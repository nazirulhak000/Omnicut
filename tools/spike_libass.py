"""
Spike script to probe libass capabilities and limits.
Tests 8 specific questions defined in Round 3.1:
1. Mid-line \\t with different time windows in a single Dialogue line
2. \\t accel parameter (0.5 vs 1.0 vs 3.0) and mid-point scale
3. Spacing interaction with \\fscx
4. Spacing: per-glyph vs per-cluster in Thai
5. Mid-line {\\1c} impact on HarfBuzz Thai runs
6. \\pos wrapping behavior at MarginL/R
7. Face selection for \\fn Kanit + Bold=1
8. Thai 2nd-level tone mark collapse with Spacing=0 vs Spacing=0.5
"""

import os
import re
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = "02_Assets/Fonts"
SCRATCH_DIR = ROOT / "tests" / "scratch_spike"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)


def render_ass(ass_text: str, duration: float, seek_time: float, out_name: str, force_style: str = None) -> Path:
    ass_path = SCRATCH_DIR / f"{out_name}.ass"
    ass_path.write_text(ass_text, encoding="utf-8")
    
    rel_ass = f"tests/scratch_spike/{out_name}.ass"
    out_png = SCRATCH_DIR / f"{out_name}.png"
    
    sub_filter = f"subtitles='{rel_ass}':fontsdir='{FONTS_DIR}'"
    if force_style:
        sub_filter += f":force_style='{force_style}'"
        
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=#000000:s=1080x1920:d={duration}",
        "-ss", str(seek_time),
        "-vf", sub_filter,
        "-frames:v", "1",
        str(out_png)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {res.stderr}")
    return out_png


def get_bbox(png_path: Path):
    im = Image.open(png_path).convert("L")
    return im.getbbox()


def make_ass(dialogues: list, styles: list = None) -> str:
    if not styles:
        styles = [
            "Style: Default,Kanit,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.5,0,1,0,0,2,60,60,400,1"
        ]
    style_block = "\n".join(styles)
    dialogue_block = "\n".join(dialogues)
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_block}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{dialogue_block}
"""


def spike_1_midline_t():
    print("\n--- [Spike 1] Mid-line \\t multiple windows in one line ---")
    # Dialogue from 0 to 2s. Word A animates 0-500ms (\fscx100 -> \fscx200), Word B starts at 100 then animates 500-1000ms (\fscx100 -> \fscx200)
    dialogues = [
        r"Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\an7\pos(100,200)\fscx100}{\t(0,500,\fscx200)}AAA {\fscx100\t(500,1000,\fscx200)}BBB"
    ]
    ass = make_ass(dialogues)
    p_250 = render_ass(ass, 2.0, 0.25, "s1_250ms")
    p_500 = render_ass(ass, 2.0, 0.50, "s1_500ms")
    p_750 = render_ass(ass, 2.0, 0.75, "s1_750ms")
    p_1000 = render_ass(ass, 2.0, 1.00, "s1_1000ms")
    
    b_250 = get_bbox(p_250)
    b_500 = get_bbox(p_500)
    b_750 = get_bbox(p_750)
    b_1000 = get_bbox(p_1000)
    print(f"Total width @ 250ms:  {b_250[2]-b_250[0]}px")
    print(f"Total width @ 500ms:  {b_500[2]-b_500[0]}px")
    print(f"Total width @ 750ms:  {b_750[2]-b_750[0]}px")
    print(f"Total width @ 1000ms: {b_1000[2]-b_1000[0]}px")
    
    works = (b_250[2]-b_250[0] < b_500[2]-b_500[0] < b_750[2]-b_750[0] < b_1000[2]-b_1000[0])
    print(f"-> Result: {'PASS (independent mid-line \\t windows work with state reset)' if works else 'FAIL'}")
    return works


def spike_2_accel_exponent():
    print("\n--- [Spike 2] \\t accel parameter (0.5 vs 1.0 vs 3.0) ---")
    # We animate \fscx from 100 to 200 over 0 to 1000ms.
    # At t=500ms, progress p=0.5:
    # accel=1.0 -> factor=0.5 -> fscx=150
    # accel=0.5 -> factor=sqrt(0.5)=0.7071 -> fscx=170.7
    # accel=3.0 -> factor=0.5^3=0.125 -> fscx=112.5
    for accel in [0.5, 1.0, 3.0]:
        d = [f"Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{{\\an7\\pos(100,200)}}{{\\t(0,1000,{accel},\\fscx200)}}MMMM"]
        p = render_ass(make_ass(d), 2.0, 0.5, f"s2_accel_{accel}")
        bbox = get_bbox(p)
        w = bbox[2] - bbox[0]
        print(f"accel={accel} at t=0.5s -> bbox width: {w}px")
    # Base at 100%
    d_base = [r"Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\an7\pos(100,200)}{\fscx100}MMMM"]
    d_200 = [r"Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\an7\pos(100,200)}{\fscx200}MMMM"]
    w_base = get_bbox(render_ass(make_ass(d_base), 2.0, 0.0, "s2_base"))[2] - get_bbox(render_ass(make_ass(d_base), 2.0, 0.0, "s2_base"))[0]
    w_200 = get_bbox(render_ass(make_ass(d_200), 2.0, 0.0, "s2_200"))[2] - get_bbox(render_ass(make_ass(d_200), 2.0, 0.0, "s2_200"))[0]
    print(f"Base 100% width: {w_base}px, Full 200% width: {w_200}px")
    return True


def spike_3_spacing_fscx():
    print("\n--- [Spike 3] Does Spacing scale with \\fscx? ---")
    # Compare text "ABCDE" with Spacing=20:
    # Case A: \fscx100, Spacing=20
    # Case B: \fscx200, Spacing=20
    # Also Case C: \fscx200, Spacing=0
    # Also Case D: \fscx100, Spacing=0
    styles_sp0 = ["Style: Sp0,Kanit,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,0,0,2,60,60,400,1"]
    styles_sp20 = ["Style: Sp20,Kanit,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,20,0,1,0,0,2,60,60,400,1"]
    
    d_sp0_100 = [r"Dialogue: 0,0:00:00.00,0:00:01.00,Sp0,,0,0,0,,{\an7\pos(100,200)\fscx100}ABCDE"]
    d_sp0_200 = [r"Dialogue: 0,0:00:00.00,0:00:01.00,Sp0,,0,0,0,,{\an7\pos(100,200)\fscx200}ABCDE"]
    d_sp20_100 = [r"Dialogue: 0,0:00:00.00,0:00:01.00,Sp20,,0,0,0,,{\an7\pos(100,200)\fscx100}ABCDE"]
    d_sp20_200 = [r"Dialogue: 0,0:00:00.00,0:00:01.00,Sp20,,0,0,0,,{\an7\pos(100,200)\fscx200}ABCDE"]
    
    w_sp0_100 = get_bbox(render_ass(make_ass(d_sp0_100, styles_sp0), 1.0, 0.0, "s3_sp0_100"))
    w_sp0_200 = get_bbox(render_ass(make_ass(d_sp0_200, styles_sp0), 1.0, 0.0, "s3_sp0_200"))
    w_sp20_100 = get_bbox(render_ass(make_ass(d_sp20_100, styles_sp20), 1.0, 0.0, "s3_sp20_100"))
    w_sp20_200 = get_bbox(render_ass(make_ass(d_sp20_200, styles_sp20), 1.0, 0.0, "s3_sp20_200"))
    
    diff_100 = (w_sp20_100[2] - w_sp20_100[0]) - (w_sp0_100[2] - w_sp0_100[0])
    diff_200 = (w_sp20_200[2] - w_sp20_200[0]) - (w_sp0_200[2] - w_sp0_200[0])
    
    print(f"Extra width from Spacing=20 @ fscx=100: {diff_100}px (for 4 gaps -> ~{diff_100/4:.1f}px/gap)")
    print(f"Extra width from Spacing=20 @ fscx=200: {diff_200}px (for 4 gaps -> ~{diff_200/4:.1f}px/gap)")
    ratio = diff_200 / diff_100 if diff_100 else 0
    print(f"Spacing scaling ratio: {ratio:.2f}x (expected 2.0x if scaled with \\fscx)")
    return True


def spike_4_spacing_thai_glyphs():
    print("\n--- [Spike 4] Spacing in Thai: per-glyph vs per-cluster ---")
    # Word: "กิ๊ก" (ก + ิ + ๊ + ก) -> 2 base consonants, 1 vowel, 1 tone mark
    # If per-glyph, spacing adds between base and vowel/tone!
    # If per-cluster, spacing only adds between กิ๊ก's clusters!
    styles = [
        "Style: Sp0,Kanit,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,0,0,2,60,60,400,1",
        "Style: Sp40,Kanit,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,40,0,1,0,0,2,60,60,400,1"
    ]
    p_sp0 = render_ass(make_ass([r"Dialogue: 0,0:00:00.00,0:00:01.00,Sp0,,0,0,0,,{\an7\pos(100,200)}กิ๊ก"], styles), 1.0, 0.0, "s4_thai_sp0")
    p_sp40 = render_ass(make_ass([r"Dialogue: 0,0:00:00.00,0:00:01.00,Sp40,,0,0,0,,{\an7\pos(100,200)}กิ๊ก"], styles), 1.0, 0.0, "s4_thai_sp40")
    
    b_0 = get_bbox(p_sp0)
    b_40 = get_bbox(p_sp40)
    w_diff = (b_40[2] - b_40[0]) - (b_0[2] - b_0[0])
    print(f"Width diff for 'กิ๊ก' with Spacing=40: {w_diff}px")
    # 'กิ๊ก' has 4 unicode chars, but 2 clusters. If 1 gap between clusters -> diff = 40px. If per-glyph -> diff = 3 * 40 = 120px!
    print(f"Number of gaps added = {w_diff / 40.0:.2f}")
    return True


def spike_5_midline_color_harfbuzz():
    print("\n--- [Spike 5] Mid-line {\\1c} span effect on HarfBuzz Thai runs ---")
    # Test 'เพิ่งเปิด' vs 'เพิ่{\1c&H00FFFF&}งเปิด' vs 'เพิ่ง{\1c&H00FFFF&}เปิด'
    d_clean = [r"Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,{\an7\pos(100,200)}เพิ่งเปิด"]
    d_split_cluster = [r"Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,{\an7\pos(100,200)}เพิ่{\1c&H00FFFF&}งเปิด"]
    d_split_word = [r"Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,{\an7\pos(100,200)}เพิ่ง{\1c&H00FFFF&}เปิด"]
    
    p_clean = render_ass(make_ass(d_clean), 1.0, 0.0, "s5_clean")
    p_split_c = render_ass(make_ass(d_split_cluster), 1.0, 0.0, "s5_split_c")
    p_split_w = render_ass(make_ass(d_split_word), 1.0, 0.0, "s5_split_w")
    
    # Compare bounding boxes and visual diffs
    b_clean = get_bbox(p_clean)
    b_split_c = get_bbox(p_split_c)
    b_split_w = get_bbox(p_split_w)
    print(f"Clean bbox:         {b_clean}")
    print(f"Split inside word:  {b_split_c}")
    print(f"Split between word: {b_split_w}")
    return True


def spike_6_pos_wrap_margin():
    print("\n--- [Spike 6] Does \\pos wrap at MarginL/R? ---")
    # Render a line longer than PlayResX (1080) with \\pos and with/without \\q2
    long_text = "ข้อความยาวมากที่เกินขอบจอแน่นอนเพื่อทดสอบการตัดคำอัตโนมัติของ libass ในกรณีที่มี pos"
    d_q0 = [f"Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,{{\\an7\\pos(100,200)}}{long_text}"]
    d_q2 = [f"Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,{{\\an7\\pos(100,200)\\q2}}{long_text}"]
    
    p_q0 = render_ass(make_ass(d_q0), 1.0, 0.0, "s6_q0")
    p_q2 = render_ass(make_ass(d_q2), 1.0, 0.0, "s6_q2")
    
    b_q0 = get_bbox(p_q0)
    b_q2 = get_bbox(p_q2)
    h_q0 = b_q0[3] - b_q0[1]
    h_q2 = b_q2[3] - b_q2[1]
    print(f"Height with default wrapping (q0): {h_q0}px (multi-line if > 100px)")
    print(f"Height with no wrapping (q2):      {h_q2}px")
    print(f"Width with default wrapping (q0):  {b_q0[2] - b_q0[0]}px")
    print(f"Width with no wrapping (q2):       {b_q2[2] - b_q2[0]}px")
    return True


def spike_7_kanit_bold_face():
    print("\n--- [Spike 7] Face selection for \\fn Kanit + Bold=1 vs Kanit Black vs Kanit-Bold ---")
    # Style 1: Fontname=Kanit, Bold=1
    # Style 2: Fontname=Kanit-Bold, Bold=0
    # Style 3: Fontname=Kanit-Black, Bold=0
    # Style 4: Fontname=Kanit Black, Bold=0
    styles = [
        "Style: K1,Kanit,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,0,0,2,60,60,400,1",
        "Style: K2,Kanit-Bold,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,0,0,2,60,60,400,1",
        "Style: K3,Kanit-Black,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,0,0,2,60,60,400,1",
        "Style: K4,Kanit Black,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,0,0,2,60,60,400,1",
    ]
    p_k1 = render_ass(make_ass([r"Dialogue: 0,0:00:00.00,0:00:01.00,K1,,0,0,0,,{\an7\pos(100,200)}ทดสอบ Kanit Bold 123"], styles), 1.0, 0.0, "s7_k1")
    p_k2 = render_ass(make_ass([r"Dialogue: 0,0:00:00.00,0:00:01.00,K2,,0,0,0,,{\an7\pos(100,200)}ทดสอบ Kanit Bold 123"], styles), 1.0, 0.0, "s7_k2")
    p_k3 = render_ass(make_ass([r"Dialogue: 0,0:00:00.00,0:00:01.00,K3,,0,0,0,,{\an7\pos(100,200)}ทดสอบ Kanit Bold 123"], styles), 1.0, 0.0, "s7_k3")
    p_k4 = render_ass(make_ass([r"Dialogue: 0,0:00:00.00,0:00:01.00,K4,,0,0,0,,{\an7\pos(100,200)}ทดสอบ Kanit Bold 123"], styles), 1.0, 0.0, "s7_k4")
    
    im_k1 = Image.open(p_k1)
    im_k2 = Image.open(p_k2)
    im_k3 = Image.open(p_k3)
    im_k4 = Image.open(p_k4)
    
    diff_k1_k2 = ImageChops.difference(im_k1, im_k2).getbbox()
    diff_k1_k3 = ImageChops.difference(im_k1, im_k3).getbbox()
    diff_k1_k4 = ImageChops.difference(im_k1, im_k4).getbbox()
    
    print(f"Diff between (Kanit, Bold=1) and Kanit-Bold:  {diff_k1_k2} (None = identical!)")
    print(f"Diff between (Kanit, Bold=1) and Kanit-Black: {diff_k1_k3}")
    print(f"Diff between (Kanit, Bold=1) and Kanit Black: {diff_k1_k4}")
    return True


def spike_8_thai_tone_spacing():
    print("\n--- [Spike 8] Backlog Thai tone mark collapse: Spacing=0 vs Spacing=0.5 ---")
    words = ["เพิ่ง", "สิ่ง", "ซื้อ", "นี้"]
    test_line = " ".join(words)
    
    styles = [
        "Style: Sp05,Prompt,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.5,0,1,0,0,2,60,60,400,1",
        "Style: Sp00,Prompt,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.0,0,1,0,0,2,60,60,400,1",
    ]
    p_05 = render_ass(make_ass([f"Dialogue: 0,0:00:00.00,0:00:01.00,Sp05,,0,0,0,,{{\\an7\\pos(100,200)}}{test_line}"], styles), 1.0, 0.0, "s8_prompt_sp05")
    p_00 = render_ass(make_ass([f"Dialogue: 0,0:00:00.00,0:00:01.00,Sp00,,0,0,0,,{{\\an7\\pos(100,200)}}{test_line}"], styles), 1.0, 0.0, "s8_prompt_sp00")
    
    b_05 = get_bbox(p_05)
    b_00 = get_bbox(p_00)
    print(f"BBox Prompt with Spacing=0.5: {b_05} (h={b_05[3]-b_05[1]})")
    print(f"BBox Prompt with Spacing=0.0: {b_00} (h={b_00[3]-b_00[1]})")
    
    # Check Kanit too
    styles_k = [
        "Style: K_Sp05,Kanit,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.5,0,1,0,0,2,60,60,400,1",
        "Style: K_Sp00,Kanit,75,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0.0,0,1,0,0,2,60,60,400,1",
    ]
    p_k_05 = render_ass(make_ass([f"Dialogue: 0,0:00:00.00,0:00:01.00,K_Sp05,,0,0,0,,{{\\an7\\pos(100,200)}}{test_line}"], styles_k), 1.0, 0.0, "s8_kanit_sp05")
    p_k_00 = render_ass(make_ass([f"Dialogue: 0,0:00:00.00,0:00:01.00,K_Sp00,,0,0,0,,{{\\an7\\pos(100,200)}}{test_line}"], styles_k), 1.0, 0.0, "s8_kanit_sp00")
    b_k_05 = get_bbox(p_k_05)
    b_k_00 = get_bbox(p_k_00)
    print(f"BBox Kanit with Spacing=0.5:  {b_k_05} (h={b_k_05[3]-b_k_05[1]})")
    print(f"BBox Kanit with Spacing=0.0:  {b_k_00} (h={b_k_00[3]-b_k_00[1]})")
    return True


if __name__ == "__main__":
    spike_1_midline_t()
    spike_2_accel_exponent()
    spike_3_spacing_fscx()
    spike_4_spacing_thai_glyphs()
    spike_5_midline_color_harfbuzz()
    spike_6_pos_wrap_margin()
    spike_7_kanit_bold_face()
    spike_8_thai_tone_spacing()
