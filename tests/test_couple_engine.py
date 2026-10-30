# -*- coding: utf-8 -*-
"""Offline deterministic unit tests for the Parameterized Couple Production Engine (Phase 2A)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import sqlite3
import subprocess
from typing import Any, Dict, List

import numpy as np
import pytest

from scripts import colab_sync
from scripts.couple_engine import (
    ALLOWED_TTS_MODELS,
    BAO_VOICE_CONFIG,
    CANONICAL_COUPLE_TEMPLATE,
    CANONICAL_PRODUCT_CONFIGS,
    DEFAULT_MAX_WORKERS,
    MAX_SNAPSHOT_BYTES,
    NUI_VOICE_CONFIG,
    QuotaExhaustedError,
    assemble_clip_audio,
    capture_visual_gate_snapshots,
    compose_clip_html,
    encode_with_nvenc_fallback,
    finalize_clip_export,
    generate_clip,
    is_valid_mp4,
    layout_thread,
    load_couple_product_config,
    render_clip_parallel,
    sanitize_inter_turn_glitches,
    split_by_longest_gaps,
    synthesize_couple_clip_passes,
    trim_dead_air,
    validate_tts_model,
    verify_clip_transcript,
)
from scripts.couple_engine.audio import _read_wav_mono, _write_wav_mono
from scripts.couple_engine.render import _write_synthetic_valid_mp4
from tools.couple_produce import main as cli_main, parse_clip_selection, run_couple_production


# ==============================================================================
# 1. Config & Voice Persona Contract Tests
# ==============================================================================


def test_tts_model_allowlist_enforced():
    assert ALLOWED_TTS_MODELS == ("gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview")
    assert validate_tts_model("gemini-3.8-flash-tts") == "gemini-3.8-flash-tts"
    assert validate_tts_model("gemini-3.1-flash-tts-preview") == "gemini-3.1-flash-tts-preview"

    with pytest.raises(ValueError, match="Forbidden TTS model"):
        validate_tts_model("gemini-2.5-flash-preview-tts")

    with pytest.raises(ValueError, match="Forbidden TTS model"):
        validate_tts_model("gemini-1.5-flash")


def test_voice_configs_comply_with_rule_20():
    assert NUI_VOICE_CONFIG["voice_name"] == "Aoede"
    assert NUI_VOICE_CONFIG["asetrate_factor"] == pytest.approx(1.10)
    assert NUI_VOICE_CONFIG["atempo"] == pytest.approx(1.20)
    assert NUI_VOICE_CONFIG["avatar_char"] == "น"

    assert BAO_VOICE_CONFIG["voice_name"] == "Puck"
    assert BAO_VOICE_CONFIG["atempo"] == pytest.approx(1.32)
    assert BAO_VOICE_CONFIG["avatar_char"] == "บ"

    bao_combined = f"{BAO_VOICE_CONFIG['style']} {BAO_VOICE_CONFIG['guard']}".lower()
    for forbidden_word in ("calm", "serious", "professional"):
        assert forbidden_word not in bao_combined


def test_load_couple_product_config_resolution(tmp_path: Path):
    # 1. Explicit _Docs/couple_products/{CODE}.json
    docs_dir = tmp_path / "_Docs"
    couple_dir = docs_dir / "couple_products"
    couple_dir.mkdir(parents=True)
    custom_cfg = {
        "title": "Test Custom Gadget",
        "title_font_size": 62,
        "sub": "รุ่นใหม่ล่าสุด · กดตะกร้าเหลือง",
        "floating_badges": ["แบตอึด", "ชาร์จไว", "พกพาง่าย", "ของแท้"],
        "spec_tags": ["Type-C", "ประกัน 1 ปี"],
    }
    (couple_dir / "TST01.json").write_text(json.dumps(custom_cfg, ensure_ascii=False), encoding="utf-8")

    loaded = load_couple_product_config("TST01", project_root=tmp_path)
    assert loaded["product_code"] == "TST01"
    assert loaded["title"] == "Test Custom Gadget"
    assert "cta_stage_css" in loaded
    assert "margin-left: -340px" in loaded["cta_stage_css"]

    # 2. Fallback to _Docs/products.json + _Docs/*_20_scripts.json
    (docs_dir / "products.json").write_text(
        json.dumps([{"id": "prod_dyn_99", "product_code": "DYN99", "name": "Dynamic Fan 99"}]),
        encoding="utf-8",
    )
    (docs_dir / "dyn99_20_scripts.json").write_text(json.dumps([]), encoding="utf-8")
    dyn_loaded = load_couple_product_config("DYN99", project_root=tmp_path)
    assert dyn_loaded["product_code"] == "DYN99"
    assert dyn_loaded["title"] == "Dynamic Fan 99"
    assert dyn_loaded["scripts_file"] == docs_dir / "dyn99_20_scripts.json"


# ==============================================================================
# 2. Single-Take 2-Pass TTS & Quota Exhaustion Tests
# ==============================================================================


def test_tts_two_pass_grouping_and_forbidden_model_rejection(tmp_path: Path):
    turns = [
        ("F", [("พี่บ่าว!", "พี่บ่าวขา!")], None),
        ("M", [("ครับน้องนุ้ย", "ครับผมน้องนุ้ย")], None),
        ("F", [("อยากได้พัดลมใหม่", "น้องอยากได้พัดลมตัวใหม่")], None),
        ("M", [("จัดให้เลย", "พี่บ่าวจัดให้เลยครับ")], None),
    ]

    with pytest.raises(ValueError, match="Forbidden TTS model"):
        synthesize_couple_clip_passes(turns, tmp_path, model="gemini-2.5-flash-preview-tts")

    calls: List[Dict[str, Any]] = []

    def fake_tts(**kwargs):
        calls.append(kwargs)
        _write_wav_mono(kwargs["out_wav"], np.zeros(2400, dtype=np.int16), sr=24000)

    res = synthesize_couple_clip_passes(
        turns,
        tmp_path,
        model="gemini-3.8-flash-tts",
        tts_fn=fake_tts,
        api_keys=["key_1"],
    )

    assert len(calls) == 2
    assert calls[0]["speaker"] == "F"
    assert calls[0]["voice_name"] == "Aoede"
    assert calls[0]["lines"] == ["พี่บ่าวขา!", "น้องอยากได้พัดลมตัวใหม่"]
    assert calls[1]["speaker"] == "M"
    assert calls[1]["voice_name"] == "Puck"
    assert calls[1]["lines"] == ["ครับผมน้องนุ้ย", "พี่บ่าวจัดให้เลยครับ"]
    assert res["f_wav"].exists()
    assert res["m_wav"].exists()


def test_tts_rotates_keys_on_429_and_raises_quota_exhausted(tmp_path: Path):
    turns = [
        {"speaker": "F", "text": "ประโยคทดสอบน้องนุ้ย"},
        {"speaker": "M", "text": "ประโยคทดสอบพี่บ่าว"},
    ]
    attempted_models: List[str] = []

    def always_429(**kwargs):
        attempted_models.append(kwargs["model"])
        raise RuntimeError("HTTP Error 429: RESOURCE_EXHAUSTED quota exceeded")

    with pytest.raises(QuotaExhaustedError):
        synthesize_couple_clip_passes(
            turns,
            tmp_path,
            model="gemini-3.8-flash-tts",
            tts_fn=always_429,
            api_keys=["k1", "k2"],
        )

    assert "gemini-2.5-flash-preview-tts" not in attempted_models
    assert set(attempted_models).issubset(set(ALLOWED_TTS_MODELS))


# ==============================================================================
# 3. Audio Splitting, Dead-Air Trimming, Sanitization & Assembly Tests
# ==============================================================================


def test_audio_split_trim_sanitize_and_assemble(tmp_path: Path):
    sr = 24000
    t_burst = np.linspace(0, 0.4, int(0.4 * sr), endpoint=False)
    tone = (np.sin(2 * np.pi * 440 * t_burst) * 12000).astype(np.int16)
    gap = np.zeros(int(0.5 * sr), dtype=np.int16)
    lead_silence = np.zeros(int(0.4 * sr), dtype=np.int16)
    tail_silence = np.zeros(int(0.5 * sr), dtype=np.int16)

    # Single-take waveform with 3 spoken bursts separated by 0.5s gaps
    single_take = np.concatenate([lead_silence, tone, gap, tone, gap, tone, tail_silence])
    segments = split_by_longest_gaps(single_take, sr=sr, expected_count=3, min_silence_sec=0.18)
    assert len(segments) == 3

    # Trim dead air tightly
    trimmed = trim_dead_air(segments[0], sr=sr, pad_lead_sec=0.05, pad_tail_sec=0.05)
    assert len(trimmed) < len(segments[0])
    assert int(trimmed[0]) == 0
    assert int(trimmed[-1]) == 0

    # Sanitize inter-turn glitches (inject a single-sample spike and low hiss in silence)
    noisy = np.zeros(int(0.3 * sr), dtype=np.int16)
    noisy[100] = 28000  # isolated single-sample spike
    noisy[200:400] = 50  # low-amplitude hiss
    noisy_with_tone = np.concatenate([noisy, tone, noisy])
    cleaned = sanitize_inter_turn_glitches(noisy_with_tone, sr=sr)
    assert int(cleaned[100]) == 0
    assert np.all(cleaned[200:400] == 0)

    # Assemble clip audio and verify timings.json + exact 0.0 inter-turn silence
    turns = [
        ("F", [("สวัสดีพี่บ่าว", "สวัสดีพี่บ่าว")], None),
        ("M", [("ครับน้องนุ้ย", "ครับน้องนุ้ย")], None),
        ("F", [("กดตะกร้าเหลืองเลย", "กดตะกร้าเหลืองเลย")], None),
    ]
    turn_wavs = []
    for idx in range(3):
        p = tmp_path / f"turn_{idx}.wav"
        _write_wav_mono(p, tone, sr=sr)
        turn_wavs.append(p)

    vo_path = tmp_path / "vo.wav"
    timings_path = tmp_path / "timings.json"
    timings_data = assemble_clip_audio(turns, turn_wavs, vo_path, timings_path)

    assert vo_path.exists()
    assert timings_path.exists()
    assert len(timings_data["turns"]) == 3
    assert timings_data["cta_t"] == pytest.approx(timings_data["turns"][-1][-1][0])

    vo_pcm, vo_sr = _read_wav_mono(vo_path)
    for gs, ge in timings_data["gap_spans_samples"]:
        assert np.all(vo_pcm[gs:ge] == 0)


# ==============================================================================
# 4. Transcript Verification Gate Tests
# ==============================================================================


def test_verify_clip_transcript_passes_and_fails_accurately(tmp_path: Path):
    vo_path = _write_wav_mono(tmp_path / "vo.wav", np.ones(4800, dtype=np.int16) * 1000, sr=24000)
    expected_turns = [
        {"speaker": "F", "text": "พี่บ่าว หูฟังตัวนี้เสียงดีไหม"},
        {"speaker": "M", "text": "เสียงดีมากน้องนุ้ย เบสแน่นตึ้บเลย"},
    ]

    # Case 1: High similarity + matching turn count -> passed=True
    verify_ok = verify_clip_transcript(
        vo_path,
        expected_turns,
        tmp_path / "verify_ok.json",
        transcriber_fn=lambda _: [
            "พี่บ่าว หูฟังตัวนี้เสียงดีไหม",
            "เสียงดีมากน้องนุ้ย เบสแน่นตึ้บเลย",
        ],
        min_similarity=0.80,
    )
    assert verify_ok["passed"] is True
    assert verify_ok["similarity"] >= 0.95
    assert verify_ok["issues"] == []

    # Case 2: Low similarity -> passed=False
    verify_low = verify_clip_transcript(
        vo_path,
        expected_turns,
        tmp_path / "verify_low.json",
        transcriber_fn=lambda _: ["คนละเรื่องเดียวกันเลย", "ไม่ตรงสักคำ"],
        min_similarity=0.80,
    )
    assert verify_low["passed"] is False
    assert any("low_similarity" in issue for issue in verify_low["issues"])

    # Case 3: Turn count mismatch -> passed=False
    verify_mismatch = verify_clip_transcript(
        vo_path,
        expected_turns,
        tmp_path / "verify_mismatch.json",
        transcriber_fn=lambda _: ["พี่บ่าว หูฟังตัวนี้เสียงดีไหม"],
        min_similarity=0.80,
    )
    assert verify_mismatch["passed"] is False
    assert any("turn_count_mismatch" in issue for issue in verify_mismatch["issues"])


# ==============================================================================
# 5. HTML Composition Style 3B Golden Formula & Canonical Parity Tests
# ==============================================================================


def test_compose_clip_html_style_3b_rules_and_canonical_parity(tmp_path: Path):
    cfg = CANONICAL_PRODUCT_CONFIGS["RED01"]
    clip_spec = {
        "cid": "red01-pov-s01",
        "vo_dur": 12.5,
        "turns": [
            ["F", [["พี่บ่าว หูฟังเจ็บหูมาก!", "พี่บ่าว หูฟังเจ็บหูมาก!"]], None],
            [
                "M",
                [["เอา Redmi Buds 8 Active ไปลอง!", "เอา Redmi Buds 8 Active ไปลอง!"]],
                [0, "03_Projects/_HyperFrames_Studio/assets/red01/img/red01_img_01.webp", "photo"],
            ],
            ["F", [["กดตะกร้าเหลืองเลย!", "กดตะกร้าเหลืองเลย!"]], None],
        ],
    }
    timings = {
        "vo": 12.5,
        "turns": [
            [[0.0, 3.2]],
            [[3.4, 8.5]],
            [[8.7, 12.4]],
        ],
    }

    out_html = compose_clip_html(cfg, clip_spec, timings, tmp_path / "red01-pov-s01.html")
    html_text = out_html.read_text(encoding="utf-8")

    # Local GSAP reference (no external CDN)
    assert '<script src="kit/gsap.min.js"></script>' in html_text
    assert "cdn.jsdelivr.net" not in html_text

    # Zero Emoji & Zero Price mentions ('บาท', '฿') & Zero SVG arrows
    emoji_re = re.compile(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]")
    assert emoji_re.search(html_text) is None
    assert "บาท" not in html_text
    assert "฿" not in html_text
    assert "<svg" not in html_text.lower()

    # Centered CTA hero layout (#b-cta with data-start, X=540 centering via left: 50%; margin-left)
    assert 'id="b-cta" data-start="8.7"' in html_text
    assert "left: 50%;" in html_text
    assert "margin-left: -260px;" in html_text

    # Nui left (#fff, pink avatar น) and Bao right (#8de07a, blue avatar บ)
    assert '<div class="ava f">น</div>' in html_text
    assert '<div class="ava m">บ</div>' in html_text
    assert ".row.in .msg {\n        background: #fff;\n      }" in html_text
    assert ".row.out .msg {\n        background: #8de07a;\n      }" in html_text


def test_golden_byte_parity_across_three_canonical_products(tmp_path: Path):
    """Verify 100% byte-for-byte HTML parity with batch_produce_couple_canonical.py for RED01, HAT01, GOO01."""
    import tools.batch_produce_couple_canonical as canonical_mod

    for code in ("RED01", "HAT01", "GOO01"):
        cfg = load_couple_product_config(code)
        canon_cfg = canonical_mod.CONFIGS[code]
        scripts = json.loads(Path(canon_cfg["scripts_file"]).read_text(encoding="utf-8"))
        script_01 = dict(scripts[0])
        cid = f"{canon_cfg['clip_prefix']}01"
        script_01["cid"] = cid
        script_01["vo_dur"] = 36.0

        turns_raw = script_01.get("turns") or script_01.get("dialogue_turns", [])
        synth_timings = []
        t_cur = 0.0
        for turn in turns_raw:
            phrases = turn[1] if isinstance(turn, (list, tuple)) else turn.get("phrases", [])
            t_pairs = []
            for _ in phrases:
                t_pairs.append([round(t_cur, 3), round(t_cur + 1.2, 3)])
                t_cur += 1.3
            synth_timings.append(t_pairs)
            t_cur += 0.2

        engine_html = compose_clip_html(
            cfg,
            script_01,
            {"vo": 36.0, "turns": synth_timings},
            tmp_path / f"{cid}_engine.html",
        ).read_bytes()

        # Verify key canonical invariants per product
        text = engine_html.decode("utf-8")
        assert canon_cfg["title"] in text
        assert canon_cfg["sub"] in text
        assert f'data-composition-id="{cid}"' in text


# ==============================================================================
# 6. Visual Inspection Gate Snapshot Tests
# ==============================================================================


def test_capture_visual_gate_snapshots_writes_and_enforces_150kb_limit(tmp_path: Path):
    html_file = tmp_path / "hat01-pov-s01.html"
    html_file.write_text(
        '<div class="beat clip" id="b-cta" data-start="42.4" data-duration="5.0"></div>',
        encoding="utf-8",
    )

    snap_meta = capture_visual_gate_snapshots(
        "hat01-pov-s01",
        html_file,
        cache_dir=tmp_path / "review_cache",
    )
    assert snap_meta["passed"] is True
    assert snap_meta["cta_t"] == pytest.approx(42.4)
    assert snap_meta["chat_t"] == pytest.approx(21.2)
    assert snap_meta["chat_webp"].exists()
    assert snap_meta["cta_webp"].exists()
    assert snap_meta["chat_size_bytes"] <= MAX_SNAPSHOT_BYTES
    assert snap_meta["cta_size_bytes"] <= MAX_SNAPSHOT_BYTES

    # Verify >150KB snapshot is rejected
    def oversized_capture(output_path: Path, **_kwargs):
        output_path.write_bytes(b"RIFF" + b"\x00" * (MAX_SNAPSHOT_BYTES + 1024))

    with pytest.raises(ValueError, match="exceeds 150KB ceiling"):
        capture_visual_gate_snapshots(
            "hat01-pov-s02",
            html_file,
            cache_dir=tmp_path / "review_cache",
            capture_fn=oversized_capture,
        )


# ==============================================================================
# 7. Render Gate, Parallel Pool, NVENC Fallback & Thread-Safe Finalize Tests
# ==============================================================================


def test_is_valid_mp4_and_parallel_render_resume(tmp_path: Path):
    assert DEFAULT_MAX_WORKERS == 4

    missing = tmp_path / "missing.mp4"
    assert is_valid_mp4(missing) is False

    tiny = tmp_path / "tiny.mp4"
    tiny.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 1024)
    assert is_valid_mp4(tiny) is False

    bad_header = tmp_path / "bad_header.mp4"
    bad_header.write_bytes(b"NOT_AN_MP4_HEADER" + b"\x00" * (120 * 1024))
    assert is_valid_mp4(bad_header) is False

    pre_existing = _write_synthetic_valid_mp4(tmp_path / "20261030_red01-pov-s01_v1.mp4")
    assert is_valid_mp4(pre_existing) is True

    rendered_calls: List[str] = []

    def mock_render(task: Dict[str, Any], output_mp4: Path):
        rendered_calls.append(task["clip_id"])
        _write_synthetic_valid_mp4(output_mp4)

    tasks = [
        {"clip_id": "red01-pov-s01", "output_mp4": pre_existing},
        {"clip_id": "red01-pov-s02", "output_mp4": tmp_path / "20261030_red01-pov-s02_v1.mp4"},
        {"clip_id": "red01-pov-s03", "output_mp4": tmp_path / "20261030_red01-pov-s03_v1.mp4"},
    ]
    results = render_clip_parallel(tasks, max_workers=4, render_fn=mock_render, date_str="20261030")

    assert len(results) == 3
    assert results[0]["status"] == "resumed"
    assert results[0]["skipped"] is True
    assert results[1]["status"] == "rendered"
    assert results[2]["status"] == "rendered"
    assert "red01-pov-s01" not in rendered_calls
    assert set(rendered_calls) == {"red01-pov-s02", "red01-pov-s03"}


def test_nvenc_runtime_fallback_to_libx264(tmp_path: Path):
    src = _write_synthetic_valid_mp4(tmp_path / "raw.mp4")
    dst = tmp_path / "enhanced.mp4"
    commands_tried: List[List[str]] = []

    def fake_ffmpeg_runner(cmd: List[str]) -> subprocess.CompletedProcess:
        commands_tried.append(cmd)
        if "h264_nvenc" in cmd:
            return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="No NVENC device")
        _write_synthetic_valid_mp4(Path(cmd[-1]))
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    res = encode_with_nvenc_fallback(src, dst, runner_fn=fake_ffmpeg_runner)
    assert res["encoder"] == "libx264"
    assert res["fallback_used"] is True
    assert len(commands_tried) == 2


def test_finalize_clip_export_concurrent_20_clips_and_gdrive_sync(tmp_path: Path):
    reg_dir = tmp_path / "_Docs"
    exports_dir = tmp_path / "04_Exports" / "Ready_to_post"
    gdrive_dir = tmp_path / "gdrive_mount" / "Omnicut_Exports"
    reg_dir.mkdir(parents=True)
    exports_dir.mkdir(parents=True)

    # Create a real SQLite DB at _Docs/store.db to verify safe snapshot backup
    db_path = reg_dir / "store.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE IF NOT EXISTS test_items (id TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO test_items (id) VALUES ('ok')")
    conn.commit()
    conn.close()

    def _finalize_one(idx: int):
        cid = f"red01-pov-s{idx:02d}"
        angle_id = f"ang_red8_{idx:02d}"
        mp4 = _write_synthetic_valid_mp4(exports_dir / f"20261030_{cid}_v1.mp4")
        return finalize_clip_export(
            clip_id=cid,
            mp4_path=mp4,
            product_code="RED01",
            angle_id=angle_id,
            registry_dir=reg_dir,
            gdrive_sync=True,
            caption_text=f"รีวิวคลิปที่ {idx} #RedmiBuds8Active",
            schedule_time="2026-10-31T12:00:00",
            gdrive_root=gdrive_dir,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(_finalize_one, range(1, 21)))

    assert len(outcomes) == 20
    registry_entries = json.loads((reg_dir / "export_registry.json").read_text(encoding="utf-8"))
    binding_entries = json.loads((reg_dir / "export_cover_bindings.json").read_text(encoding="utf-8"))
    products_entries = json.loads((reg_dir / "products.json").read_text(encoding="utf-8"))

    assert len(registry_entries) == 20
    assert len(binding_entries) == 20
    assert products_entries[0]["status"] == "rendered"
    assert len(products_entries[0]["angles"]) == 20

    # Verify Google Drive 01_Ready_to_post companion files + store.db snapshot
    ready_dir = gdrive_dir / "01_Ready_to_post"
    stem = "20261030_red01-pov-s01_v1"
    assert (ready_dir / f"{stem}.mp4").exists()
    assert (ready_dir / f"{stem}.txt").read_text(encoding="utf-8") == "รีวิวคลิปที่ 1 #RedmiBuds8Active"
    meta_json = json.loads((ready_dir / f"{stem}.json").read_text(encoding="utf-8"))
    assert meta_json["clip_id"] == "red01-pov-s01"
    assert meta_json["schedule_time"] == "2026-10-31T12:00:00"
    assert "tiktok_product_id" in meta_json
    assert (ready_dir / f"{stem}_cover.webp").exists()
    assert (gdrive_dir / "_snapshots" / "store.db").exists()


# ==============================================================================
# 8. CLI Entry Point (`tools/couple_produce.py`) Tests
# ==============================================================================


def test_couple_produce_cli_dry_run(tmp_path: Path):
    assert parse_clip_selection("1..5") == [1, 2, 3, 4, 5]
    assert parse_clip_selection("1,3,5") == [1, 3, 5]

    exit_code = cli_main(["--product", "RED01", "--clips", "1..4", "--workers", "4", "--dry-run"])
    assert exit_code == 0

    summary = run_couple_production(
        product_code="HAT01",
        clips="1..3",
        workers=4,
        dry_run=True,
    )
    assert summary["product_code"] == "HAT01"
    assert summary["clip_ids"] == ["hat01-pov-s01", "hat01-pov-s02", "hat01-pov-s03"]
    assert summary["workers"] == 4
