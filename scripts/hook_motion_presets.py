"""Labels for the hook banner's motion presets, served to the editor's pickers.

Backend-authoritative, same shape as it_angles.py's catalogs: the key IS the
id that crosses the wire, and the frontend renders whatever this returns
rather than hardcoding its own copy -- so adding a preset here plus a builder
in subtitle_engine.py is all it takes for it to show up in the UI.

The animation itself lives in subtitle_engine.py's HOOK_*_BUILDERS registries;
these dicts carry only display text. Keys must stay in sync with those
registries (guarded by a test).
"""

from scripts.subtitle.motion_contract import get_motion_preset

HOOK_IN_PRESETS = {
    "bounce": {"label_th": "เด้งเข้า", "label_en": "Bounce"},
    "bounce_soft": {"label_th": "เด้งนุ่ม", "label_en": "Soft Bounce"},
    "elastic_bounce": {"label_th": "เด้งดึ๋ง", "label_en": "Elastic Bounce"},
    "pop": {"label_th": "ป็อป", "label_en": "Pop"},
    "pop_soft": {"label_th": "ป็อปนุ่ม", "label_en": "Soft Pop"},
    "slam": {"label_th": "กระแทกจอ", "label_en": "3D Slam"},
    "fade": {"label_th": "จางเข้า", "label_en": "Fade"},
    "zoom": {"label_th": "ซูมเข้า", "label_en": "Zoom"},
    "slide_up": {"label_th": "เลื่อนขึ้น", "label_en": "Slide Up"},
    "typewriter": {"label_th": "พิมพ์ดีด", "label_en": "Typewriter"},
    "blur": {"label_th": "เบลอเข้าโฟกัส", "label_en": "Blur In"},
    "none": {"label_th": "ไม่มี", "label_en": "None"},
}

HOOK_REVEAL_PRESETS = {
    "simultaneous": {"label_th": "ขึ้นพร้อมกัน", "label_en": "Simultaneous"},
    "cumulative": {"label_th": "สะสมทีละบรรทัด", "label_en": "Cumulative Lines"},
    "tier_step": {"label_th": "ทยอยทีละบรรทัด", "label_en": "Step-by-Step"},
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


def _with_renderer_capabilities(catalog, phase=None):
    annotated = {}
    for preset_id, value in catalog.items():
        contract = get_motion_preset("hook", phase, preset_id) if phase else None
        contract_meta = (contract or {}).get("metadata") or {}
        contract_bound = bool(contract_meta.get("renderer_bound")) if contract else False
        binding = "motion_contract" if contract_bound else "legacy_overlay_renderer"
        parity_level = contract_meta.get("parity_level") or "legacy"
        annotated[preset_id] = {
            **value,
            "enabled": True,
            "preview_bound": True,
            "render_bound": True,
            "contract_renderer_bound": contract_bound,
            "binding": binding,
            "parity_level": parity_level,
            "unsupported_tracks": list(contract_meta.get("unsupported_tracks") or []),
        }
    return annotated


def hook_motion_catalog():
    """All pickers in one payload, in the order the UI shows them."""
    return {
        "in": _with_renderer_capabilities(HOOK_IN_PRESETS, "in"),
        "reveal": _with_renderer_capabilities(HOOK_REVEAL_PRESETS),
        "loop": _with_renderer_capabilities(HOOK_LOOP_PRESETS, "loop"),
        "out": _with_renderer_capabilities(HOOK_OUT_PRESETS, "out"),
        "accent": _with_renderer_capabilities(HOOK_ACCENT_PRESETS),
    }


def hook_motion_capability_summary():
    entries = [
        item
        for group in hook_motion_catalog().values()
        for item in group.values()
    ]
    return {
        "total": len(entries),
        "enabled": sum(bool(item["enabled"]) for item in entries),
        "preview_bound": sum(bool(item["preview_bound"]) for item in entries),
        "render_bound": sum(bool(item["render_bound"]) for item in entries),
        "contract_bound": sum(bool(item["contract_renderer_bound"]) for item in entries),
        "legacy_fallback": sum(item["binding"] == "legacy_overlay_renderer" for item in entries),
        "blocked": sum(not bool(item["enabled"]) for item in entries),
    }
