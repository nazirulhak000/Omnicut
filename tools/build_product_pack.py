import json
import shutil
from pathlib import Path

def create_pack():
    base_dir = Path(".tmp/gadget_products/Xiaomi_MIX_Flip")
    base_dir.mkdir(parents=True, exist_ok=True)
    photos_dir = base_dir / "photos"
    photos_dir.mkdir(exist_ok=True)

    # Copy video
    src_video = Path(".tmp/xiaomi_mix_flip_1080p.mp4")
    dst_video = base_dir / "video_clean_1080p.mp4"
    if src_video.exists():
        shutil.copy2(src_video, dst_video)

    # Copy extracted sample frames
    for f in [".tmp/mix_flip_frame_10s.jpg", ".tmp/mix_flip_frame_25s.jpg"]:
        p = Path(f)
        if p.exists():
            shutil.copy2(p, photos_dir / p.name)

    # Create info.json
    info = {
        "product_id": "xiaomi-mix-flip",
        "brand": "Xiaomi",
        "model": "MIX Flip",
        "tagline": "มือถือจอพับตลับแป้งตัวแรก จอนอกใหญ่สุด 4.01 นิ้ว",
        "specs": {
            "outer_display": "4.01 inch 120Hz AMOLED",
            "inner_display": "6.86 inch 1-120Hz LTPO",
            "chipset": "Snapdragon 8 Gen 3",
            "cameras": "50MP Light Hunter 800 + 50MP 2x Telephoto (Leica)",
            "battery": "4780mAh + 67W HyperCharge"
        },
        "content_hooks": [
            "Xiaomi MIX Flip มือถือจอพับตลับแป้งเครื่องแรก จอนอกทำอะไรได้บ้าง คุ้มราคาไหม?",
            "จอนอก 4.01 นิ้ว ใหญ่ขนาดนี้ แทบไม่ต้องกางจอจริงไหม?",
            "สเปก Snapdragon 8 Gen 3 ในบอดี้จอพับ เรื่องความร้อนเป็นยังไง?"
        ],
        "rights_basis": "official_design_film_clean_broll",
        "status": "ready_for_editing"
    }
    (base_dir / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Xiaomi MIX Flip product pack created successfully!")

if __name__ == "__main__":
    create_pack()
