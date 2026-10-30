"""
Batch Auto-Link Script for Unlinked Export Clips in OmniCut Pro Studio.
Maps 30 external/legacy export clips to their corresponding products in ProductStore,
ensures ExportRegistry row has product_id and angle_id,
and extracts 540x960 WebP thumbnails for TikTok Helper Extension parity.
"""

import json
import subprocess
import sys
from pathlib import Path

# Set stdout encoding for Windows console
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.product_store import ProductStore
from scripts.export_registry import ExportRegistry
from scripts.channel_scope import ChannelScope
from scripts.api_exports import list_exports

# 30 Mapping Specifications
CLIPS_SPECS = [
    # Group 1: LOOP Smartband (02a82b8dbfbf4cdf97bb59643f9d295b)
    {
        "filename": "loop01-pov-chat-28s.mp4",
        "product_id": "02a82b8dbfbf4cdf97bb59643f9d295b",
        "angle_id": "ang_legacy_loop01_pov_chat_28s",
        "angle_name": "💬 POV Chat: รีวิวสายรัดข้อมือ LOOP Smartband (28s)",
        "hook_title": "POV: สายรัดข้อมืออัจฉริยะ วัดชีพจร นับก้าว แบตอึดสะใจ!",
        "caption": "สายรัดข้อมือ LOOP Smartband ฟังก์ชันครบทั้งนับก้าว วัดชีพจร แจ้งเตือนข้อความ พิกัดในตะกร้าเลย 👇",
        "hashtags": "#LOOPSmartband #สายรัดข้อมือเพื่อสุขภาพ #สมาร์ทแบนด์ #รีวิวของดี #พิกัดในตะกร้า",
    },
    {
        "filename": "BCD01-POV_Chat_1_20261010_160500.mp4",
        "product_id": "02a82b8dbfbf4cdf97bb59643f9d295b",
        "angle_id": "ang_legacy_bcd01_pov_chat_1",
        "angle_name": "💬 POV Chat: สายรัดข้อมืออัจฉริยะ LOOP Smartband ชีวิตเปลี่ยน",
        "hook_title": "POV: แฟนบ่นไม่ดูแลตัวเอง ลองใช้สมาร์ทแบนด์ตัวนี้ดู!",
        "caption": "ชีวิตเปลี่ยนเมื่อมี LOOP Smartband ตัวช่วยดูแลสุขภาพครบวงจร พิกัดในตะกร้าเลย 👇",
        "hashtags": "#LOOPSmartband #สมาร์ทแบนด์ #รักสุขภาพ #TikTokป้ายยา #พิกัดในตะกร้า",
    },

    # Group 2: Hatari พัดลมตั้งโต๊ะ 16 นิ้ว (c6eca50968f04431849b6464aacb6f89)
    {
        "filename": "hat01-meme-45s.mp4",
        "product_id": "c6eca50968f04431849b6464aacb6f89",
        "angle_id": "ang_legacy_hat01_meme_45s",
        "angle_name": "🔥 มีมคลายร้อน: Hatari 16 นิ้ว ลมแรงสะใจระดับพายุ (45s)",
        "hook_title": "POV: ร้อนตับแตกขนาดนี้ ต้องเปิดพัดลมฮาตาริเบอร์ 3!",
        "caption": "ร้อนเบอร์นี้มีแค่ Hatari 16 นิ้วเท่านั้นที่เอาอยู่ ลมแรงสะใจ ทนทานระดับตำนาน พิกัดในตะกร้าเลย 👇",
        "hashtags": "#Hatari #พัดลมฮาตาริ #พัดลม16นิ้ว #คลายร้อน #รีวิวของใช้ในบ้าน #พิกัดในตะกร้า",
    },

    # Group 3: GoChek รุ่น GC-ULTRA S24 (7d2fa34272ef4404a5784a9c6e627fb0)
    {
        "filename": "goc01-spec-42s.mp4",
        "product_id": "7d2fa34272ef4404a5784a9c6e627fb0",
        "angle_id": "ang_legacy_goc01_spec_42s",
        "angle_name": "🎙️ เจาะสเปกไมค์ไร้สาย GoChek GC-ULTRA S24 ตัดเสียงรบกวนเทพ (42s)",
        "hook_title": "POV: ไมค์ไร้สายตัวจบ สเปกเทพตัดเสียงรอบข้างเนียนกริบ!",
        "caption": "ไมค์ไร้สาย GoChek GC-ULTRA S24 เสียงใสคมชัด ตัดเสียงรบกวนรอบข้างได้เนียนกริบ พิกัดในตะกร้าเลย 👇",
        "hashtags": "#GoChek #ไมค์ไร้สาย #ไมค์ติดเสื้อ #รีวิวไมค์ #TikTokป้ายยา #พิกัดในตะกร้า",
    },
    {
        "filename": "goc01-pov5-plug.mp4",
        "product_id": "7d2fa34272ef4404a5784a9c6e627fb0",
        "angle_id": "ang_legacy_goc01_pov5_plug",
        "angle_name": "🔌 GoChek GC-ULTRA S24: เสียบปุ๊บติดปั๊บ ใช้งานง่ายไม่ต้องตั้งค่า",
        "hook_title": "POV: ไมค์ไร้สายแบบ Plug & Play เสียบปุ๊บพร้อมอัดเสียงทันที!",
        "caption": "ไมค์ไร้สาย GoChek GC-ULTRA S24 เสียบปุ๊บติดปั๊บ ไม่ต้องง้อบลูทูธ เสียงดีชัดเจน พิกัดในตะกร้าเลย 👇",
        "hashtags": "#GoChek #ไมค์ไร้สาย #อัดเสียง #รีวิวแกดเจ็ต #พิกัดในตะกร้า",
    },
    {
        "filename": "goc01-pov4-dual.mp4",
        "product_id": "7d2fa34272ef4404a5784a9c6e627fb0",
        "angle_id": "ang_legacy_goc01_pov4_dual",
        "angle_name": "👥 GoChek GC-ULTRA S24: ไมค์คู่ 2 ตัว สัมภาษณ์พร้อมกันเสียงไม่มีดรอป",
        "hook_title": "POV: สัมภาษณ์คู่ ถ่ายคลิป 2 คน ไมค์ตัวเดียวเอาไม่อยู่!",
        "caption": "ถ่ายคลิป 2 คนต้องไมค์คู่ GoChek GC-ULTRA S24 เสียงคมชัดทั้งสองฝั่ง พิกัดในตะกร้าเลย 👇",
        "hashtags": "#GoChek #ไมค์คู่ #ไมค์สัมภาษณ์ #คอนเทนต์ครีเอเตอร์ #พิกัดในตะกร้า",
    },
    {
        "filename": "goc01-pov3-bat.mp4",
        "product_id": "7d2fa34272ef4404a5784a9c6e627fb0",
        "angle_id": "ang_legacy_goc01_pov3_bat",
        "angle_name": "🔋 GoChek GC-ULTRA S24: แบตอึดสะใจ พร้อมเคสชาร์จพกพาสบาย",
        "hook_title": "POV: ถ่ายงานทั้งวัน แบตไมค์หมดกลางคันคือฝันร้าย!",
        "caption": "ถ่ายงานนอกสถานที่ยาวๆ สบายใจ ด้วย GoChek GC-ULTRA S24 แบตอึดพร้อมกล่องชาร์จ พิกัดในตะกร้าเลย 👇",
        "hashtags": "#GoChek #ไมค์ไร้สาย #แบตอึด #ถ่ายคลิป #พิกัดในตะกร้า",
    },
    {
        "filename": "goc01-pov2-wall.mp4",
        "product_id": "7d2fa34272ef4404a5784a9c6e627fb0",
        "angle_id": "ang_legacy_goc01_pov2_wall",
        "angle_name": "🧱 GoChek GC-ULTRA S24: สัญญาณทะลุกำแพง เดินไกล 50 เมตรเสียงไม่กระตุก",
        "hook_title": "POV: เดินไกลแค่ไหน สัญญาณก็ไม่หลุด ไม่ขาดตอน!",
        "caption": "ส่งสัญญาณไกล เสถียรสุดๆ GoChek GC-ULTRA S24 เสียงชัดเป๊ะทุกก้าว พิกัดในตะกร้าเลย 👇",
        "hashtags": "#GoChek #ไมค์ไร้สาย #เสียงคมชัด #พิกัดในตะกร้า",
    },
    {
        "filename": "goc01-pov1-anc.mp4",
        "product_id": "7d2fa34272ef4404a5784a9c6e627fb0",
        "angle_id": "ang_legacy_goc01_pov1_anc",
        "angle_name": "🔇 GoChek GC-ULTRA S24: ระบบ Active Noise Cancelling ตัดเสียงลมเสียงรถ",
        "hook_title": "POV: อัดคลิปริมถนน ลมพัดแรง แต่เสียงพูดยังชัดแจ๋ว!",
        "caption": "ระบบตัดเสียงรบกวนระดับโปร GoChek GC-ULTRA S24 เสียงรอบข้างหายเกลี้ยง เหลือแต่เสียงเรา พิกัดในตะกร้าเลย 👇",
        "hashtags": "#GoChek #ตัดเสียงรบกวน #ไมค์ตัดเสียง #TikTokป้ายยา #พิกัดในตะกร้า",
    },
    {
        "filename": "goc01-pov-32s.mp4",
        "product_id": "7d2fa34272ef4404a5784a9c6e627fb0",
        "angle_id": "ang_legacy_goc01_pov_32s",
        "angle_name": "⚡ GoChek GC-ULTRA S24: สรุปใน 32 วินาที ทำไมครีเอเตอร์ต้องมี",
        "hook_title": "POV: ครีเอเตอร์มือใหม่ อยากเสียงดีระดับโปร ต้องตัวนี้!",
        "caption": "ไมค์ไร้สาย GoChek GC-ULTRA S24 ยกระดับคุณภาพเสียงคลิปของคุณให้ดูเป็นมืออาชีพ พิกัดในตะกร้าเลย 👇",
        "hashtags": "#GoChek #ครีเอเตอร์ #ไมค์ไร้สาย #รีวิวของดี #พิกัดในตะกร้า",
    },

    # Group 4: ที่ชาร์จเร็ว, Essager, PD 30W (9505b042d58640f5aa58015bb86be097)
    {
        "filename": "ess02-vs-25s.mp4",
        "product_id": "9505b042d58640f5aa58015bb86be097",
        "angle_id": "ang_legacy_ess02_vs_25s",
        "angle_name": "🆚 เทียบหัวชาร์จเก่า vs Essager PD 30W ชาร์จเร็วกว่า 3 เท่า (25s)",
        "hook_title": "POV: เทียบหัวชาร์จเก่า 5W vs Essager PD 30W เร็วกว่าเห็นๆ!",
        "caption": "เทียบให้เห็นจะๆ หัวชาร์จ Essager PD 30W ไวกว่าหัวเดิม 3 เท่า ขนาดจิ๋วพกพาสะดวก พิกัดในตะกร้าเลย 👇",
        "hashtags": "#Essager #หัวชาร์จเร็ว #หัวชาร์จ30W #เทียบของ #พิกัดในตะกร้า",
    },
    {
        "filename": "ess02-review-30s.mp4",
        "product_id": "9505b042d58640f5aa58015bb86be097",
        "angle_id": "ang_legacy_ess02_review_30s",
        "angle_name": "⭐ รีวิวสปีดหัวชาร์จ Essager PD 30W แบตพุ่งทันใจ (30s)",
        "hook_title": "POV: รีวิวหัวชาร์จจิ๋วแต่แจ๋ว Essager 30W แบตขึ้นไวเวอร์!",
        "caption": "รีวิวหัวชาร์จ Essager PD 30W ชาร์จไว ไม่ร้อน พกง่ายตัวเดียวจบ พิกัดในตะกร้าเลย 👇",
        "hashtags": "#Essager #รีวิวหัวชาร์จ #หัวชาร์จไว #TikTokป้ายยา #พิกัดในตะกร้า",
    },
    {
        "filename": "ess02-pov5-cool60.mp4",
        "product_id": "9505b042d58640f5aa58015bb86be097",
        "angle_id": "ang_legacy_ess02_pov5_cool60",
        "angle_name": "❄️ Essager PD 30W: ชิปอัจฉริยะคุมอุณหภูมิ ชาร์จไวเครื่องไม่ร้อน (60s)",
        "hook_title": "POV: ชาร์จไวแต่เครื่องไม่ร้อน มีชิปคุมอุณหภูมิปลอดภัย 100%!",
        "caption": "หมดกังวลเรื่องเครื่องร้อน แบตบวม Essager PD 30W มีชิประบายความร้อนในตัว พิกัดในตะกร้าเลย 👇",
        "hashtags": "#Essager #หัวชาร์จไม่ร้อน #ถนอมแบต #หัวชาร์จไอโฟน #พิกัดในตะกร้า",
    },
    {
        "filename": "ess02-pov4-worth60.mp4",
        "product_id": "9505b042d58640f5aa58015bb86be097",
        "angle_id": "ang_legacy_ess02_pov4_worth60",
        "angle_name": "💡 Essager PD 30W: ความคุ้มค่าราคาหลักร้อย คุณภาพระดับพรีเมียม (60s)",
        "hook_title": "POV: ราคาหลักร้อย คุณภาพหลักพัน คุ้มกว่านี้ไม่มีอีกแล้ว!",
        "caption": "หัวชาร์จ Essager PD 30W จ่ายน้อยแต่ได้ความเร็วเต็มสปีด พิกัดในตะกร้าเลย 👇",
        "hashtags": "#Essager #คุ้มค่า #หัวชาร์จเร็ว #ของดีราคาถูก #พิกัดในตะกร้า",
    },
    {
        "filename": "ess02-pov3-mini60.mp4",
        "product_id": "9505b042d58640f5aa58015bb86be097",
        "angle_id": "ang_legacy_ess02_pov3_mini60",
        "angle_name": "🤏 Essager PD 30W: ขนาดจิ๋วเท่านิ้วก้อย ไม่กินที่เต้าเสียบ (60s)",
        "hook_title": "POV: หัวชาร์จจิ๋วเบาเท่านิ้วก้อย เสียบปลั๊กไม่เบียดใคร!",
        "caption": "เล็กกะทัดรัด พกพาสะดวก Essager PD 30W ไม่เกะกะปลั๊กอื่น พิกัดในตะกร้าเลย 👇",
        "hashtags": "#Essager #หัวชาร์จจิ๋ว #พกพาสะดวก #หัวชาร์จเร็ว #พิกัดในตะกร้า",
    },
    {
        "filename": "ess02-pov2-safe60.mp4",
        "product_id": "9505b042d58640f5aa58015bb86be097",
        "angle_id": "ang_legacy_ess02_pov2_safe60",
        "angle_name": "🛡️ Essager PD 30W: ระบบป้องกันไฟ 6 ชั้น ปลอดภัยหายห่วง (60s)",
        "hook_title": "POV: หัวชาร์จราคาถูกแต่เซฟตี้ 6 ชั้น กันไฟกระชาก ชาร์จทิ้งไว้ได้เลย!",
        "caption": "ปลอดภัยทุกการชาร์จ Essager PD 30W มีระบบกันไฟกระชาก ตัดไฟอัตโนมัติ พิกัดในตะกร้าเลย 👇",
        "hashtags": "#Essager #ระบบความปลอดภัย #หัวชาร์จเร็ว #TikTokป้ายยา #พิกัดในตะกร้า",
    },
    {
        "filename": "ess02-pov1-fast60.mp4",
        "product_id": "9505b042d58640f5aa58015bb86be097",
        "angle_id": "ang_legacy_ess02_pov1_fast60",
        "angle_name": "⚡ Essager PD 30W: สปีดแรง 0-60% ใน 30 นาที สำหรับ iPhone & iPad (60s)",
        "hook_title": "POV: รีบออกจากบ้าน แบตเหลือ 5% เสียบตัวนี้ 30 นาทีพุ่ง 60%!",
        "caption": "ชาร์จไวทันใจในชั่วโมงเร่งด่วน Essager PD 30W ตัวช่วยคนชอบลืมชาร์จแบต พิกัดในตะกร้าเลย 👇",
        "hashtags": "#Essager #ชาร์จไว #หัวชาร์จ30W #หัวชาร์จไอโฟน #พิกัดในตะกร้า",
    },
    {
        "filename": "ess02-pov-chat-28s.mp4",
        "product_id": "9505b042d58640f5aa58015bb86be097",
        "angle_id": "ang_legacy_ess02_pov_chat_28s",
        "angle_name": "💬 POV Chat: เม้าท์แฟนแย่งหัวชาร์จ Essager PD 30W (28s)",
        "hook_title": "POV: แฟนแอบจิ๊กหัวชาร์จไปใช้ เพราะชาร์จไวกว่าของตัวเอง!",
        "caption": "โดนแย่งหัวชาร์จตลอด! Essager PD 30W ตัวนี้ชาร์จไวใครๆ ก็ชอบ พิกัดในตะกร้าเลย 👇",
        "hashtags": "#Essager #POV #แฟนแย่งของ #หัวชาร์จเร็ว #พิกัดในตะกร้า",
    },
    {
        "filename": "ess02-jaokum-22s.mp4",
        "product_id": "9505b042d58640f5aa58015bb86be097",
        "angle_id": "ang_legacy_ess02_jaokum_22s",
        "angle_name": "🎬 สไตล์ละครสั้น: เจ้ากรรมนายเวรมาในคราบหัวชาร์จเต่าคลาน (22s)",
        "hook_title": "POV: ชาร์จทั้งคืนขึ้นมา 10% เลิกทนกับหัวชาร์จเก่าได้แล้ว!",
        "caption": "เปลี่ยนมาใช้ Essager PD 30W ชีวิตดีขึ้นทันตา ชาร์จไวไม่เสียอารมณ์ พิกัดในตะกร้าเลย 👇",
        "hashtags": "#Essager #หัวชาร์จเร็ว #เรื่องตลก #ฮาๆ #พิกัดในตะกร้า",
    },
    {
        "filename": "ess02-hype-25s.mp4",
        "product_id": "9505b042d58640f5aa58015bb86be097",
        "angle_id": "ang_legacy_ess02_hype_25s",
        "angle_name": "🔥 ป้ายยาไฟลุก: Essager PD 30W หัวชาร์จยอดฮิต TikTok (25s)",
        "hook_title": "POV: หัวชาร์จที่คนรีวิวเยอะที่สุดใน TikTok ดีจริงไหม?!",
        "caption": "ของแท้แน่นอน Essager PD 30W การันตีความไวและปลอดภัย รีบกดก่อนหมดโปร พิกัดในตะกร้าเลย 👇",
        "hashtags": "#Essager #ป้ายยา #TikTokของดี #หัวชาร์จเร็ว #พิกัดในตะกร้า",
    },
    {
        "filename": "ess02-explainer-40s.mp4",
        "product_id": "9505b042d58640f5aa58015bb86be097",
        "angle_id": "ang_legacy_ess02_explainer_40s",
        "angle_name": "🔬 อธิบายวิทย์: ทำไม Essager PD 30W หัวเล็กแต่จ่ายไฟแรง (40s)",
        "hook_title": "POV: ทำไมหัวชาร์จบางตัวชาร์จไว แต่บางตัวชาร์จช้า?!",
        "caption": "เจาะลึกเทคโนโลยีชิปจ่ายไฟ Essager PD 30W ให้กำลังไฟเต็ม 30W สปีดไม่ตก พิกัดในตะกร้าเลย 👇",
        "hashtags": "#Essager #ความรู้ไอที #เทคโนโลยี #หัวชาร์จ30W #พิกัดในตะกร้า",
    },
    {
        "filename": "ess02-battery-36s.mp4",
        "product_id": "9505b042d58640f5aa58015bb86be097",
        "angle_id": "ang_legacy_ess02_battery_36s",
        "angle_name": "🚨 กู้ชีพแบต 1%: Essager PD 30W เสียบปุ๊บฟื้นปั๊บ (36s)",
        "hook_title": "POV: แบตเหลือ 1% อีก 10 นาทีต้องพรีเซนต์งาน!",
        "caption": "นาทีชีวิต Essager PD 30W ชาร์จแป๊บเดียวแบตขึ้นมาพร้อมลุยงานต่อ พิกัดในตะกร้าเลย 👇",
        "hashtags": "#Essager #แบตหมด #กู้ชีพแบต #หัวชาร์จเร็ว #พิกัดในตะกร้า",
    },
    {
        "filename": "ess02-asmr-26s.mp4",
        "product_id": "9505b042d58640f5aa58015bb86be097",
        "angle_id": "ang_legacy_ess02_asmr_26s",
        "angle_name": "🎧 ASMR No Talking: สัมผัสความแน่นและกะทัดรัด Essager PD 30W (26s)",
        "hook_title": "POV: เสียงเสียบปลั๊กแน่นๆ ฟินๆ กับหัวชาร์จ Essager 30W",
        "caption": "สัมผัสงานประกอบพรีเมียม ขาพับแน่นหนา Essager PD 30W พิกัดในตะกร้าเลย 👇",
        "hashtags": "#Essager #ASMR #หัวชาร์จ #ของดีบอกต่อ #พิกัดในตะกร้า",
    },

    # Group 5: Orsen by Eloop S6 240W (37521e0dae1a419e8037e159254d4fdf)
    {
        "filename": "els6-pov-chat-30s.mp4",
        "product_id": "37521e0dae1a419e8037e159254d4fdf",
        "angle_id": "ang_legacy_els6_pov_chat_30s",
        "angle_name": "💬 POV Chat: สายชาร์จ Orsen S6 ทนทาน 240W โน้ตบุ๊กแบตแดง (30s)",
        "hook_title": "POV: แฟนเปิดโน้ตบุ๊กแบต 3% อีก 10 นาทีต้องพรีเซนต์งาน!",
        "caption": "สายชาร์จตัวจบ Orsen S6 จ่ายไฟแรง 240W ชาร์จได้ทั้งโน้ตบุ๊กและมือถือ ถักสายแน่นไม่ขาดง่าย พิกัดในตะกร้าเลย 👇",
        "hashtags": "#OrsenS6 #สายชาร์จ240W #สายชาร์จโน้ตบุ๊ก #TikTokป้ายยา #พิกัดในตะกร้า",
    },
    {
        "filename": "els6-couple-paper.mp4",
        "product_id": "37521e0dae1a419e8037e159254d4fdf",
        "angle_id": "ang_legacy_els6_couple_paper",
        "angle_name": "📜 คู่รักกระดาษยับ: สายชาร์จขาวพังอีกแล้ว Orsen S6 มาช่วย (Paper Chat)",
        "hook_title": "POV: สายชาร์จเก่าข้อต่อฉีก ต้องงอสายค้างถึงจะเข้า!",
        "caption": "น้องนุ้ยบ่นพี่บ่าวสายชาร์จพัง! ต้องจัด Orsen by Eloop S6 สายถักเคฟลาร์ 240W ตัวจบ พิกัดในตะกร้าเลย 👇",
        "hashtags": "#OrsenS6 #น้องนุ้ยพี่บ่าว #ละครคู่รัก #สายชาร์จทนทาน #พิกัดในตะกร้า",
    },
    {
        "filename": "20261012_OrsenS6_240W_ors01-pov1-240w_v1.mp4",
        "product_id": "37521e0dae1a419e8037e159254d4fdf",
        "angle_id": "ang_legacy_ors01_pov1_240w_v1",
        "angle_name": "⚡ Orsen S6 240W: พลังชาร์จเร็วสะใจ สำหรับแล็ปท็อปและสมาร์ทโฟน (v1)",
        "hook_title": "POV: สายชาร์จเส้นเดียว ชาร์จได้ทั้งบ้าน กำลังไฟสูง 240W!",
        "caption": "ไม่ต้องพกหลายสาย Orsen S6 เส้นเดียวรองรับกำลังไฟสูงสุด 240W ชาร์จไวสะใจ พิกัดในตะกร้าเลย 👇",
        "hashtags": "#OrsenS6 #สายชาร์จPD #FastCharge #Eloop #พิกัดในตะกร้า",
    },
    {
        "filename": "ors01-pov1-240w.mp4",
        "product_id": "37521e0dae1a419e8037e159254d4fdf",
        "angle_id": "ang_legacy_ors01_pov1_240w_alt",
        "angle_name": "⚡ Orsen S6 240W: ชิป E-Marker แท้ ควบคุมกระแสไฟนิ่งสนิท",
        "hook_title": "POV: ทำไมสายชาร์จเส้นนี้ถึงจ่ายไฟได้แรงถึง 240 วัตต์?!",
        "caption": "มีชิป E-Marker คุมไฟปลอดภัย ชาร์จโน้ตบุ๊ก แล็ปท็อป มือถือ ได้เต็มประสิทธิภาพ พิกัดในตะกร้าเลย 👇",
        "hashtags": "#OrsenS6 #Eloop #สายชาร์จไว #ชาร์จโน้ตบุ๊ก #พิกัดในตะกร้า",
    },
    {
        "filename": "20261012_OrsenS6_240W_battery_1pct_fire_v1.mp4",
        "product_id": "37521e0dae1a419e8037e159254d4fdf",
        "angle_id": "ang_legacy_ors01_pov2_fire_v1",
        "angle_name": "🔥 Orsen S6: สายชาร์จถักหนา 48 เส้น ทนแรงดึง ไม่ขาดใน (v1)",
        "hook_title": "POV: เลิกซื้อสายชาร์จเดือนละเส้น สายถักไนลอนทนทานขั้นสุด!",
        "caption": "สายถักไนลอนหนาพิเศษ Orsen S6 ดัดงอได้เป็นหมื่นครั้ง ข้อต่อไม่ฉีกขาด พิกัดในตะกร้าเลย 👇",
        "hashtags": "#OrsenS6 #สายชาร์จทนๆ #สายถัก #Eloop #พิกัดในตะกร้า",
    },
    {
        "filename": "ors01-pov2-fire.mp4",
        "product_id": "37521e0dae1a419e8037e159254d4fdf",
        "angle_id": "ang_legacy_ors01_pov2_fire_alt",
        "angle_name": "🔥 Orsen S6: บททดสอบความทนทาน งอข้อต่อไม่พัง",
        "hook_title": "POV: สายชาร์จเก่าข้อต่อฉีกจนเห็นไส้ใน ลองเปลี่ยนมาใช้ตัวนี้!",
        "caption": "สายชาร์จ Orsen S6 240W เสริมซิลิโคนข้อต่อ ไม่หักไม่งอ ทนทานระดับพรีเมียม พิกัดในตะกร้าเลย 👇",
        "hashtags": "#OrsenS6 #สายชาร์จ #ของดีบอกต่อ #รีวิวแกดเจ็ต #พิกัดในตะกร้า",
    },
    {
        "filename": "_HyperFrames_Studio_2026-10-12_20-31-56.mp4",
        "product_id": "37521e0dae1a419e8037e159254d4fdf",
        "angle_id": "ang_legacy_orsen_paper_chat_master",
        "angle_name": "💬 ละครคู่รักกระดาษยับ: สายชาร์จข้อต่อฉีก ต้องงอสายค้างถึงจะเข้า! (ต้นฉบับ)",
        "hook_title": "POV: สายชาร์จเก่าข้อต่อฉีก ต้องงอสายค้าง ถึงจะเข้า!",
        "caption": "น้องนุ้ยบ่นพี่บ่าวสายชาร์จพัง! ข้อต่อฉีกจนเห็นไส้ใน เปลี่ยนมาใช้ Orsen S6 สายถัก 48 Braided พิกัดในตะกร้าเลย 👇",
        "hashtags": "#OrsenS6 #น้องนุ้ยพี่บ่าว #ละครคู่รัก #สายชาร์จทนทาน #พิกัดในตะกร้า",
    },
]


def extract_thumbnail_if_missing(video_path: Path) -> Path:
    """Extracts a 540x960 WebP thumbnail from 2.0s if not already present."""
    webp_path = video_path.with_suffix(".webp")
    if not webp_path.exists():
        cmd = [
            "ffmpeg", "-y", "-ss", "00:00:02", "-i", str(video_path),
            "-vframes", "1", "-vf", "scale=540:960", str(webp_path)
        ]
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode == 0:
            print(f"  [Thumbnail] Generated {webp_path.name}")
        else:
            print(f"  [Thumbnail] Warning: ffmpeg failed for {video_path.name}")
    return webp_path


COVERS_DIR = BASE_DIR / "05_Covers_Thumbnails"
COVER_TEMPLATES = {
    'ess02': '20261013_ess02-pov-s01_v1_cover.jpg',
    'els6': '20261014_ors01-pov-s01_v1_cover.jpg',
    'ors01': '20261014_ors01-pov-s01_v1_cover.jpg',
    '20261012_OrsenS6': '20261014_ors01-pov-s01_v1_cover.jpg',
    'goc01': 'GOC01-รีวิวสเปก_1_cover.jpg',
    'hat01': 'HAT01-รีวิวสเปก_1_cover.jpg',
    'loop01': 'BCD01-รีวิวสเปก_1_cover.jpg',
    'BCD01': 'BCD01-รีวิวสเปก_1_cover.jpg',
    '_HyperFrames_Studio': '20261014_ors01-pov-s01_v1_cover.jpg',
}


def ensure_covers_exist(stem: str):
    """Ensures 9:16 and 3:4 cover JPG files exist in 05_Covers_Thumbnails/."""
    dst_9 = COVERS_DIR / f"{stem}_cover.jpg"
    dst_3 = COVERS_DIR / f"{stem}_cover_3x4.jpg"
    if dst_9.exists() and dst_3.exists():
        return
    template_name = None
    for prefix, tpl in COVER_TEMPLATES.items():
        if stem.startswith(prefix):
            template_name = tpl
            break
    if not template_name:
        template_name = '20261014_ors01-pov-s01_v1_cover.jpg'
    
    import shutil
    src_9 = COVERS_DIR / template_name
    src_3 = COVERS_DIR / template_name.replace('_cover.jpg', '_cover_3x4.jpg')
    if src_9.exists() and not dst_9.exists():
        shutil.copyfile(src_9, dst_9)
    if src_3.exists() and not dst_3.exists():
        shutil.copyfile(src_3, dst_3)


def run_batch_auto_link(channel_id: str = "main"):
    print("=================================================================")
    print(f"🚀 Starting Batch Auto-Link for 30 Unlinked Exports (Channel: {channel_id})")
    print("=================================================================")

    # 1. Load Products to cache
    products_list = ProductStore.get_all(channel_id=channel_id)
    product_map = {p["id"]: p for p in products_list}

    # 2. Process each spec
    linked_count = 0
    for idx, spec in enumerate(CLIPS_SPECS, 1):
        filename = spec["filename"]
        prod_id = spec["product_id"]
        angle_id = spec["angle_id"]
        video_rel = f"04_Exports/Ready_to_post/{filename}"
        video_abs = BASE_DIR / video_rel

        if not video_abs.exists():
            print(f"[{idx}/30] ⚠️ File not found: {video_rel} — skipping")
            continue

        print(f"[{idx}/30] Processing: {filename} -> Product: {prod_id[:8]}... | Angle: {angle_id}")

        # A. Ensure WebP Thumbnail & 9:16/3:4 Covers exist
        extract_thumbnail_if_missing(video_abs)
        ensure_covers_exist(video_abs.stem)

        # B. Ensure & Update ExportRegistry
        export_record = ExportRegistry.ensure(
            video_abs,
            product_id=prod_id,
            angle_id=angle_id,
            status="rendered",
            channel_id=channel_id,
        )
        export_id = export_record["id"]

        # If existing record didn't update product/angle (e.g. was already in registry),
        # perform an explicit update to guarantee product_id & angle_id are stored.
        with ExportRegistry._scoped_mutate(ExportRegistry._scope(channel_id)) as records:
            for row in records:
                if str(row.get("id")) == str(export_id) or row.get("path") == video_rel:
                    row["product_id"] = prod_id
                    row["angle_id"] = angle_id
                    row["status"] = "rendered"
                    row["updated_at"] = ProductStore._now()
                    break
        ExportRegistry._invalidate_index()

        # C. Update ProductStore: Append or Update Angle
        product = product_map.get(prod_id)
        if not product:
            print(f"  ❌ Error: Product {prod_id} not found in store!")
            continue

        existing_angles = product.get("angles", [])
        matched_angle = next((a for a in existing_angles if (a.get("angle_id") or a.get("id")) == angle_id), None)

        now_str = ProductStore._now()
        stem = Path(filename).stem
        thumb_rel = f"04_Exports/Ready_to_post/{stem}.webp"
        cover_rel = f"05_Covers_Thumbnails/{stem}_cover.jpg"
        cover_3x4_rel = f"05_Covers_Thumbnails/{stem}_cover_3x4.jpg"

        angle_data = {
            "angle_id": angle_id,
            "angle_name": spec["angle_name"],
            "title": spec["angle_name"],
            "hook_title": spec["hook_title"],
            "status": "rendered",
            "video_url": video_rel,
            "export_id": export_id,
            "tiktok_caption": spec["caption"],
            "tiktok_hashtags": spec["hashtags"],
            "cover_path": cover_3x4_rel,
            "cover_3x4_path": cover_3x4_rel,
            "cover_9x16_path": cover_rel,
            "thumbnail_url": f"/api/media/{thumb_rel}",
            "updated_at": now_str,
        }

        # Check if angle already exists in product
        if matched_angle:
            # Update in place via scoped mutate
            with ProductStore._scoped_mutate(ProductStore._scope(channel_id)) as prods:
                for p in prods:
                    if p["id"] == prod_id:
                        for a in p.get("angles", []):
                            if (a.get("angle_id") or a.get("id")) == angle_id:
                                a.update(angle_data)
                                break
                        p["updated_at"] = now_str
                        break
        else:
            # Append new angle to product
            angle_data["created_at"] = now_str
            with ProductStore._scoped_mutate(ProductStore._scope(channel_id)) as prods:
                for p in prods:
                    if p["id"] == prod_id:
                        p_angles = p.setdefault("angles", [])
                        p_angles.append(angle_data)
                        p["updated_at"] = now_str
                        break

        linked_count += 1
        print(f"  ✅ Linked successfully (export_id: {export_id})")

    print("\n=================================================================")
    print(f"🎉 Successfully linked {linked_count} / {len(CLIPS_SPECS)} clips!")
    print("=================================================================\n")

    # 3. Verification
    print("🔍 Running Verification via list_exports()...")
    scope = ChannelScope(channel_id=channel_id, strict=False, source="header")
    res = list_exports(scope=scope)
    exports = res.get("exports", [])

    unlinked_now = [e for e in exports if e.get("is_unlinked")]
    latest_now = [e for e in exports if e.get("is_latest")]
    print(f"  - Total Exports: {len(exports)}")
    print(f"  - Latest Version Count: {len(latest_now)}")
    print(f"  - Unlinked Clips Count: {len(unlinked_now)}")

    if len(unlinked_now) == 0:
        print("  🌟 PERFECT: 0 unlinked clips remaining! All clips are recognized as valid ready-to-post exports.")
    else:
        print(f"  ⚠️ Note: {len(unlinked_now)} unlinked clips still present:")
        for u in unlinked_now:
            print(f"    * {u.get('name')}")

    # 4. Check Extension readiness contract
    print("\n🔍 Checking TikTok Helper Extension readiness (isReadyToPost contract)...")
    ready_count = 0
    for e in exports:
        is_ready = e.get("angle_status") == "rendered" and e.get("is_latest") is not False and not e.get("is_posted")
        if is_ready:
            ready_count += 1
    print(f"  - Clips matching isReadyToPost: {ready_count}")

if __name__ == "__main__":
    run_batch_auto_link()
