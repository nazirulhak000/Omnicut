"""Speed round phase 2: translation cache + rate-limit cooldown, scrim source length,
JSON body for unhandled server errors, CapCut draft backup. Offline and deterministic."""
import asyncio
import json
import sys
from pathlib import Path

import pytest

from scripts import translator as translator_mod
from scripts.translator import SubtitleTranslator

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


class TooManyRequests(Exception):
    """Same class name deep_translator raises; the translator matches on the name."""


@pytest.fixture()
def clean_translator(monkeypatch):
    monkeypatch.setattr(SubtitleTranslator, "_CACHE", {})
    monkeypatch.setattr(SubtitleTranslator, "_disk_cache", {})
    monkeypatch.setattr(SubtitleTranslator, "_disk_cache_path", None)
    monkeypatch.setattr(SubtitleTranslator, "_disk_dirty", False)
    monkeypatch.setattr(SubtitleTranslator, "_google_blocked_until", 0.0)
    monkeypatch.setattr(translator_mod.time, "sleep", lambda _s: None)
    return SubtitleTranslator


def _install_providers(monkeypatch, google, fallback):
    import deep_translator

    class Google:
        def __init__(self, **_kw):
            pass

        def translate(self, text):
            return google(text)

    class MyMemory:
        def __init__(self, **_kw):
            pass

        def translate(self, text):
            return fallback(text)

    monkeypatch.setattr(translator_mod, "GoogleTranslator", Google)
    monkeypatch.setattr(deep_translator, "MyMemoryTranslator", MyMemory)


PHRASES = ["คำที่หนึ่งยาวหน่อย", "คำที่สองยาวหน่อย", "คำที่สามยาวหน่อย", "คำที่สี่ยาวหน่อย", "คำที่ห้ายาวหน่อย", "คำที่หกยาวหน่อย"]


def test_rate_limited_google_is_not_retried_for_every_clause(clean_translator, monkeypatch):
    google_calls = []

    def google(text):
        google_calls.append(text)
        raise TooManyRequests()

    _install_providers(monkeypatch, google, lambda text: f"EN:{text}")
    result = clean_translator.translate_batch(PHRASES)

    assert result == [f"EN:{p}" for p in PHRASES]
    # Three workers can each be mid-request when the first refusal lands; before
    # the cooldown this was 3 attempts per clause = 18 calls.
    assert len(google_calls) <= 3


def test_other_google_errors_still_get_their_three_attempts(clean_translator, monkeypatch):
    google_calls = []

    def google(text):
        google_calls.append(text)
        raise RuntimeError("temporary hiccup")

    _install_providers(monkeypatch, google, lambda text: "fallback")
    assert clean_translator._translate_single("ข้อความทดสอบ") == "fallback"
    assert len(google_calls) == 3


def test_translations_are_reused_from_disk_after_a_restart(clean_translator, monkeypatch):
    _install_providers(monkeypatch, lambda text: f"EN:{text}", lambda text: "unused")
    first = clean_translator.translate_batch(PHRASES)
    cache_file = clean_translator._cache_file()
    assert cache_file.is_file()
    assert json.loads(cache_file.read_text(encoding="utf-8"))[PHRASES[0]] == f"EN:{PHRASES[0]}"

    # A new process: nothing in memory, and both providers are down.
    monkeypatch.setattr(SubtitleTranslator, "_CACHE", {})
    monkeypatch.setattr(SubtitleTranslator, "_disk_cache", {})
    monkeypatch.setattr(SubtitleTranslator, "_disk_cache_path", None)

    def down(_text):
        raise AssertionError("provider must not be called for a cached clause")

    _install_providers(monkeypatch, down, down)
    assert clean_translator.translate_batch(PHRASES) == first


def test_failed_translations_are_not_cached(clean_translator, monkeypatch):
    def down(_text):
        raise RuntimeError("down")

    _install_providers(monkeypatch, down, down)
    assert clean_translator.translate_batch(PHRASES[:2]) == ["", ""]
    assert not clean_translator._cache_file().exists()


def test_corrupt_cache_file_is_ignored(clean_translator, monkeypatch):
    cache_file = clean_translator._cache_file()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("{not json", encoding="utf-8")
    _install_providers(monkeypatch, lambda text: "ok", lambda text: "unused")
    assert clean_translator.translate_batch(PHRASES[:1]) == ["ok"]
    assert json.loads(cache_file.read_text(encoding="utf-8")) == {PHRASES[0]: "ok"}


def test_hook_scrim_source_stops_after_its_fade():
    source = (SCRIPTS / "video_editor.py").read_text(encoding="utf-8")
    assert "scrim_source_dur = min(total_duration + 0.5, span_end + fade_tail + 0.5)" in source
    assert "d={scrim_source_dur:.6f}[{src}];" in source
    # eof_action=pass on the scrim overlay changed 4 frames inside the fade
    # (measured with framemd5), so the overlay must keep the default.
    scrim_overlay = source.split("geq=lum='0':cb='128':cr='128'", 1)[1].split("current_v = out", 1)[0]
    assert "eof_action" not in scrim_overlay


def test_unhandled_error_answers_json_without_the_message():
    from scripts.api_server import unhandled_exception_handler

    class _Url:
        path = "/api/anything"

    class _Request:
        method = "GET"
        url = _Url()

    response = asyncio.run(unhandled_exception_handler(_Request(), RuntimeError(r"C:\Users\secret\path broke")))
    body = json.loads(response.body)
    assert response.status_code == 500
    assert body["success"] is False and body["error"] == "internal_server_error"
    assert "RuntimeError" in body["detail"]
    assert "secret" not in response.body.decode("utf-8")


def test_http_errors_keep_their_own_status(monkeypatch):
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from scripts.api_server import app

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/this-route-does-not-exist")
    assert response.status_code in (401, 403, 404)
    assert HTTPException is not None


def test_capcut_draft_is_backed_up_before_overwrite():
    source = (SCRIPTS / "agent" / "omnicut_agent_tools.py").read_text(encoding="utf-8")
    write_at = source.index("content_file.write_text(json.dumps(draft_data")
    guard = source[:write_at].rsplit("draft_data = builder._create_draft_content", 1)[1]
    assert "if content_file.is_file():" in guard
    assert "shutil.copy2(content_file, backup_file)" in guard


def test_recording_upload_probes_off_the_event_loop():
    source = (SCRIPTS / "api_recording.py").read_text(encoding="utf-8")
    assert "await asyncio.to_thread(VideoEditor.get_media_info, str(dest_path))" in source
    assert "import asyncio" in source
    assert sys.version_info >= (3, 9)
