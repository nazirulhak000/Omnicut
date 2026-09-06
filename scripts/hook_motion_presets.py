"""
Labels for the hook banner's motion presets, served to the editor's pickers.

Backend-authoritative, same shape as it_angles.py's catalogs: the key IS the
id that crosses the wire, and the frontend renders whatever this returns
rather than hardcoding its own copy -- so adding a preset here plus a builder
in subtitle_engine.py is all it takes for it to show up in the UI.

The animation itself lives in subtitle_engine.py's HOOK_*_BUILDERS registries;
these dicts carry only display text. Keys must stay in sync with those
registries (guarded by a test).
"""

HOOK_IN_PRESETS = {
    "bounce": {"label_th": "เด้งเข้า", "label_en": "Bounce"},
    "bounce_soft": {"label_th": "เด้งนุ่ม", "label_en": "Soft Bounce"},
    "pop": {"label_th": "ป็อป", "label_en": "Pop"},
    "pop_soft": {"label_th": "ป็อปนุ่ม", "label_en": "Soft Pop"},
    "fade": {"label_th": "จางเข้า", "label_en": "Fade"},
    "zoom": {"label_th": "ซูมเข้า", "label_en": "Zoom"},
    "slide_up": {"label_th": "เลื่อนขึ้น", "label_en": "Slide Up"},
    "typewriter": {"label_th": "พิมพ์ดีด", "label_en": "Typewriter"},
    "blur": {"label_th": "เบลอเข้าโฟกัส", "label_en": "Blur In"},
    "none": {"label_th": "ไม่มี", "label_en": "None"},
}

HOOK_LOOP_PRESETS = {
    "pulse": {"label_th": "เต้นเบาๆ", "label_en": "Pulse"},
    "wave": {"label_th": "โยกเป็นคลื่น", "label_en": "Wave"},
    "shake": {"label_th": "สั่น", "label_en": "Shake"},
    "flicker": {"label_th": "ไฟกระพริบ", "label_en": "Flicker"},
    "lightsweep": {"label_th": "แสงกวาด", "label_en": "Light Sweep"},
    "none": {"label_th": "ไม่มี", "label_en": "None"},
}

HOOK_OUT_PRESETS = {
    "fade": {"label_th": "จางหาย", "label_en": "Fade"},
    "slide": {"label_th": "เลื่อนลง", "label_en": "Slide"},
    "zoom": {"label_th": "ซูมออก", "label_en": "Zoom"},
    "glitch": {"label_th": "กลิตช์", "label_en": "Glitch"},
    "none": {"label_th": "ตัดหายทันที", "label_en": "Cut"},
}

HOOK_ACCENT_PRESETS = {
    "underline": {"label_th": "เส้นใต้เรืองแสง", "label_en": "Accent Bar"},
    "badge": {"label_th": "แถบไฮไลต์", "label_en": "Badge"},
    "none": {"label_th": "ไม่มี", "label_en": "None"},
}


def hook_motion_catalog():
    """All four pickers in one payload, in the order the UI shows them."""
    return {
        "in": HOOK_IN_PRESETS,
        "loop": HOOK_LOOP_PRESETS,
        "out": HOOK_OUT_PRESETS,
        "accent": HOOK_ACCENT_PRESETS,
    }
