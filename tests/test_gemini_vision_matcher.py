"""
Behavioral coverage for scripts/gemini_vision_matcher.py beyond the
retry/backoff/timeout paths already covered in tests/test_gemini_vision_retry.py
(which mocks get_or_upload_video and get_cached_matches away entirely). This
file covers what that leaves untested: cache-key derivation and its actual
read/write side effects, the file-upload/polling loop in get_or_upload_video,
malformed/truncated API response parsing, and asserting the success path
really writes to the persistent cache (the exact shape of bug this audit is
watching for -- a NameError or swallowed exception after a successful match
means the cache is never written and every future render re-pays for the
same analysis).

scripts.gemini_vision_matcher binds VISION_CACHE_FILE = ASSETS_DIR / ...  at
import time, so patching scripts.config.ASSETS_DIR alone would not affect
this module -- every test here patches gvm.VISION_CACHE_FILE directly instead
(the same approach tests/test_gemini_vision_retry.py already uses), keeping
real _Docs/02_Assets untouched. Offline: no real Gemini traffic, no real
video files, no real ffmpeg binary, no real sleeps.
"""
import hashlib
import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from google.genai import errors as genai_errors

from scripts import gemini_vision_matcher as gvm


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)


@pytest.fixture(autouse=True)
def _isolate_cache_file(monkeypatch, tmp_path):
    """Never touch the real 02_Assets/.vision_cache.json."""
    monkeypatch.setattr(gvm, "VISION_CACHE_FILE", tmp_path / ".vision_cache.json")
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "0")
    monkeypatch.setenv("DAILY_COST_THB_LIMIT", "0")


def _client_error(code: int, message: str = "err") -> genai_errors.ClientError:
    return genai_errors.ClientError(code, {"error": {"message": message, "status": "X"}}, None)


_CUES = [{"start": 0.0, "end": 2.0, "text": "หนึ่ง"}]


def _ok_response(shots=None) -> MagicMock:
    shots = shots if shots is not None else [
        {"cue_id": 1, "start_time": 0.0, "end_time": 2.0, "visual_reason": "x", "punch_zoom": 1.1}
    ]
    resp = MagicMock()
    resp.text = "```json\n" + json.dumps({"matched_shots": shots}) + "\n```"
    return resp


def _fake_client_factory(behaviors):
    created = []

    def factory(*, api_key, http_options=None):
        client = MagicMock()
        created.append(client)

        def generate_content(*, model, contents, config=None):
            behavior = behaviors.pop(0)
            if isinstance(behavior, BaseException):
                raise behavior
            return behavior

        client.models.generate_content.side_effect = generate_content
        return client

    factory.created = created
    return factory


# ------------------------------------------------------------ _compute_file_hash

def test_compute_file_hash_is_deterministic_for_same_content(tmp_path):
    f = tmp_path / "a.mp4"
    f.write_bytes(b"some video bytes" * 100)
    h1 = gvm.GeminiVisionMatcher._compute_file_hash(f)
    h2 = gvm.GeminiVisionMatcher._compute_file_hash(f)
    assert h1 == h2
    assert len(h1) == 32  # md5 hexdigest


def test_compute_file_hash_differs_for_different_size(tmp_path):
    f1 = tmp_path / "a.mp4"
    f2 = tmp_path / "b.mp4"
    f1.write_bytes(b"x" * 100)
    f2.write_bytes(b"x" * 200)
    assert gvm.GeminiVisionMatcher._compute_file_hash(f1) != gvm.GeminiVisionMatcher._compute_file_hash(f2)


def test_compute_file_hash_differs_for_different_content_same_size(tmp_path):
    f1 = tmp_path / "a.mp4"
    f2 = tmp_path / "b.mp4"
    f1.write_bytes(b"a" * 100)
    f2.write_bytes(b"b" * 100)
    assert gvm.GeminiVisionMatcher._compute_file_hash(f1) != gvm.GeminiVisionMatcher._compute_file_hash(f2)


def test_prepared_request_context_returns_cached_match_without_a_second_lookup(monkeypatch, tmp_path):
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"data")
    cached = [{"cue_id": 1, "start_time": 0.0, "end_time": 2.0}]
    file_hash = gvm.GeminiVisionMatcher._compute_file_hash(raw)
    cue_text = "|".join(cue["text"] for cue in _CUES)
    gvm.GeminiVisionMatcher._save_cache({
        "matches": {f"{file_hash}_{hashlib.md5(cue_text.encode('utf-8')).hexdigest()}": cached}
    })

    context = gvm.GeminiVisionMatcher.prepare_request_context(str(raw), _CUES)
    monkeypatch.setattr(
        gvm.GeminiVisionMatcher,
        "get_cached_matches",
        classmethod(lambda *_args: pytest.fail("prepared context must skip a second cache lookup")),
    )

    assert gvm.GeminiVisionMatcher.match_script_to_video(
        str(raw), _CUES, request_context=context
    ) == cached


# --------------------------------------------------------------- cache load/save

def test_load_cache_missing_file_returns_empty_dict():
    assert gvm.GeminiVisionMatcher._load_cache() == {}


def test_save_cache_then_load_round_trips(tmp_path):
    data = {"matches": {"key1": [{"a": 1}]}}
    gvm.GeminiVisionMatcher._save_cache(data)
    assert gvm.VISION_CACHE_FILE.exists()
    loaded = gvm.GeminiVisionMatcher._load_cache()
    assert loaded == data


def test_load_cache_corrupt_json_returns_empty_dict_not_raise():
    gvm.VISION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    gvm.VISION_CACHE_FILE.write_text("{not valid json", encoding="utf-8")
    assert gvm.GeminiVisionMatcher._load_cache() == {}


def test_save_cache_creates_parent_directory(tmp_path):
    nested = tmp_path / "deep" / "nested" / ".vision_cache.json"
    with patch.object(gvm, "VISION_CACHE_FILE", nested):
        gvm.GeminiVisionMatcher._save_cache({"x": 1})
        assert nested.exists()
        assert json.loads(nested.read_text(encoding="utf-8")) == {"x": 1}


# ----------------------------------------------------------- get_cached_matches

def test_get_cached_matches_returns_none_when_cache_empty(tmp_path):
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"video data")
    assert gvm.GeminiVisionMatcher.get_cached_matches(str(raw), _CUES) is None


def test_get_cached_matches_returns_hit_with_correct_key(tmp_path):
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"video data")

    file_hash = gvm.GeminiVisionMatcher._compute_file_hash(raw.resolve())
    cues_summary = "|".join([c.get("text", "") for c in _CUES])
    key = f"{file_hash}_{hashlib.md5(cues_summary.encode('utf-8')).hexdigest()}"

    gvm.GeminiVisionMatcher._save_cache({"matches": {key: [{"cue_id": 1, "start_time": 0.0, "end_time": 2.0}]}})

    result = gvm.GeminiVisionMatcher.get_cached_matches(str(raw), _CUES)
    assert result == [{"cue_id": 1, "start_time": 0.0, "end_time": 2.0}]


def test_get_cached_matches_different_cues_miss_the_cache(tmp_path):
    """The cache key folds in the cues text -- a script rewrite must not
    silently reuse a stale scene map for different cue text."""
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"video data")
    file_hash = gvm.GeminiVisionMatcher._compute_file_hash(raw.resolve())
    stale_key = f"{file_hash}_{hashlib.md5(b'some other cues').hexdigest()}"
    gvm.GeminiVisionMatcher._save_cache({"matches": {stale_key: [{"x": 1}]}})

    assert gvm.GeminiVisionMatcher.get_cached_matches(str(raw), _CUES) is None


def test_get_cached_matches_empty_list_entry_is_treated_as_a_miss(tmp_path):
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"video data")
    file_hash = gvm.GeminiVisionMatcher._compute_file_hash(raw.resolve())
    cues_summary = "|".join([c.get("text", "") for c in _CUES])
    key = f"{file_hash}_{hashlib.md5(cues_summary.encode('utf-8')).hexdigest()}"
    gvm.GeminiVisionMatcher._save_cache({"matches": {key: []}})

    assert gvm.GeminiVisionMatcher.get_cached_matches(str(raw), _CUES) is None


def test_get_cached_matches_missing_video_file_returns_none_not_raise(tmp_path):
    """_compute_file_hash calls filepath.stat() -- a video path that doesn't
    exist must degrade to a cache miss, not blow up match_script_to_video's
    cache-check-first codepath."""
    missing = tmp_path / "does_not_exist.mp4"
    assert gvm.GeminiVisionMatcher.get_cached_matches(str(missing), _CUES) is None


# --------------------------------------------------------------- get_or_upload_video

def test_get_or_upload_video_missing_file_returns_none(tmp_path):
    missing = tmp_path / "nope.mp4"
    client = MagicMock()
    assert gvm.GeminiVisionMatcher.get_or_upload_video(client, str(missing)) is None


def test_get_or_upload_video_cache_hit_with_active_remote_skips_upload(tmp_path):
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"video data")
    file_hash = gvm.GeminiVisionMatcher._compute_file_hash(raw.resolve())
    gvm.GeminiVisionMatcher._save_cache({file_hash: {"remote_file_name": "files/abc123"}})

    client = MagicMock()
    active_file = MagicMock()
    active_file.state.name = "ACTIVE"
    client.files.get.return_value = active_file

    result = gvm.GeminiVisionMatcher.get_or_upload_video(client, str(raw))

    assert result is active_file
    client.files.get.assert_called_once_with(name="files/abc123")
    client.files.upload.assert_not_called()


def test_get_or_upload_video_cache_hit_but_remote_gone_falls_through_to_upload(tmp_path, monkeypatch):
    """A cached remote_file_name whose file has expired server-side must not
    return None outright -- the code re-uploads instead."""
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"video data")
    file_hash = gvm.GeminiVisionMatcher._compute_file_hash(raw.resolve())
    gvm.GeminiVisionMatcher._save_cache({file_hash: {"remote_file_name": "files/gone"}})

    monkeypatch.setattr(gvm.GeminiVisionMatcher, "_vision_proxy", classmethod(lambda cls, v, h: None))

    client = MagicMock()
    client.files.get.side_effect = Exception("404 not found")
    uploaded_file = MagicMock()
    uploaded_file.state.name = "ACTIVE"
    uploaded_file.name = "files/new123"
    client.files.upload.return_value = uploaded_file

    with patch("google.genai.types.UploadFileConfig", MagicMock()):
        result = gvm.GeminiVisionMatcher.get_or_upload_video(client, str(raw))

    assert result is uploaded_file
    client.files.upload.assert_called_once()


def test_get_or_upload_video_fresh_upload_polls_until_active(tmp_path, monkeypatch):
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "_vision_proxy", classmethod(lambda cls, v, h: None))
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"video data")

    client = MagicMock()
    processing = MagicMock()
    processing.state.name = "PROCESSING"
    processing.name = "files/xyz"
    active = MagicMock()
    active.state.name = "ACTIVE"
    active.name = "files/xyz"

    client.files.upload.return_value = processing
    # First two polls still processing, third comes back active
    client.files.get.side_effect = [processing, processing, active]

    with patch("google.genai.types.UploadFileConfig", MagicMock()):
        result = gvm.GeminiVisionMatcher.get_or_upload_video(client, str(raw))

    assert result is active
    assert client.files.get.call_count == 3

    # cache actually written with the new remote file name -- the exact
    # "success path must have real side effects" class of bug this audit
    # targets
    file_hash = gvm.GeminiVisionMatcher._compute_file_hash(raw.resolve())
    cache = gvm.GeminiVisionMatcher._load_cache()
    assert cache[file_hash]["remote_file_name"] == "files/xyz"
    assert cache[file_hash]["local_path"] == str(raw.resolve())


def test_get_or_upload_video_stuck_processing_returns_none(tmp_path, monkeypatch):
    """If the file never reaches ACTIVE within the poll budget, the function
    must return None (caller falls back to cached/empty), not hang forever
    or raise."""
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "_vision_proxy", classmethod(lambda cls, v, h: None))
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"video data")

    client = MagicMock()
    stuck = MagicMock()
    stuck.state.name = "PROCESSING"
    stuck.name = "files/stuck"
    client.files.upload.return_value = stuck
    client.files.get.return_value = stuck  # always still processing

    with patch("google.genai.types.UploadFileConfig", MagicMock()):
        result = gvm.GeminiVisionMatcher.get_or_upload_video(client, str(raw))

    assert result is None
    assert client.files.get.call_count == 90  # the documented retry budget


def test_get_or_upload_video_failed_state_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "_vision_proxy", classmethod(lambda cls, v, h: None))
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"video data")

    client = MagicMock()
    failed = MagicMock()
    failed.state.name = "FAILED"
    failed.name = "files/failed"
    client.files.upload.return_value = failed

    with patch("google.genai.types.UploadFileConfig", MagicMock()):
        result = gvm.GeminiVisionMatcher.get_or_upload_video(client, str(raw))

    assert result is None


def test_get_or_upload_video_uses_proxy_when_available(tmp_path, monkeypatch):
    """_vision_proxy() returning a smaller stand-in file must be what gets
    uploaded, not the original -- the whole point of the proxy is to avoid
    uploading the camera original."""
    raw = tmp_path / "raw.mov"
    raw.write_bytes(b"huge original bytes")
    proxy = tmp_path / "proxy.mp4"
    proxy.write_bytes(b"tiny proxy bytes")

    monkeypatch.setattr(gvm.GeminiVisionMatcher, "_vision_proxy", classmethod(lambda cls, v, h: proxy))

    client = MagicMock()
    active = MagicMock()
    active.state.name = "ACTIVE"
    active.name = "files/proxy_upload"
    client.files.upload.return_value = active

    captured = {}
    real_open = open

    def fake_open(path, mode):
        captured["path"] = str(path)
        return real_open(path, mode)

    with patch("google.genai.types.UploadFileConfig", MagicMock()), \
         patch("builtins.open", side_effect=fake_open):
        result = gvm.GeminiVisionMatcher.get_or_upload_video(client, str(raw))

    assert result is active
    assert captured["path"] == str(proxy)


# ------------------------------------------------------------ match_script_to_video

def test_match_script_to_video_no_api_key_returns_empty_list(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"data")
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "get_cached_matches", classmethod(lambda cls, p, c: None))

    result = gvm.GeminiVisionMatcher.match_script_to_video(str(raw), _CUES, raw_duration=10.0)
    assert result == []


def test_match_script_to_video_cache_hit_short_circuits_before_budget_check(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"data")
    cached = [{"cue_id": 1, "start_time": 0.0, "end_time": 2.0}]
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "get_cached_matches", classmethod(lambda cls, p, c: cached))

    with patch("scripts.quota.check_budget") as mock_budget:
        result = gvm.GeminiVisionMatcher.match_script_to_video(str(raw), _CUES, raw_duration=10.0)

    assert result == cached
    mock_budget.assert_not_called()


def test_match_script_to_video_success_actually_writes_the_persistent_cache(monkeypatch, tmp_path):
    """The exact bug shape this audit is watching for: a successful match
    that returns the right value to the caller but never lands in the
    on-disk cache would silently force every future render to re-pay for
    the same Gemini call. Assert the cache file on disk actually contains
    the new match after a successful run."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "0")
    monkeypatch.setenv("DAILY_COST_THB_LIMIT", "0")
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "get_cached_matches", classmethod(lambda cls, p, c: None))
    monkeypatch.setattr(
        gvm.GeminiVisionMatcher, "get_or_upload_video",
        classmethod(lambda cls, client, path: MagicMock(name="remote_video")),
    )
    from scripts import token_tracker
    recorded = {}
    monkeypatch.setattr(token_tracker.TokenTracker, "record_event", lambda **kw: recorded.update(kw))

    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"data")

    shots = [{"cue_id": 1, "start_time": 0.0, "end_time": 2.0, "visual_reason": "hand shows product", "punch_zoom": 1.2}]
    factory = _fake_client_factory([_ok_response(shots)])

    with patch("google.genai.Client", side_effect=factory):
        result = gvm.GeminiVisionMatcher.match_script_to_video(str(raw), _CUES, raw_duration=10.0)

    assert result == shots

    # the cache on disk (not just the return value) carries the match
    file_hash = gvm.GeminiVisionMatcher._compute_file_hash(raw.resolve())
    cues_summary = "|".join([c.get("text", "") for c in _CUES])
    expected_key = f"{file_hash}_{hashlib.md5(cues_summary.encode('utf-8')).hexdigest()}"
    on_disk = json.loads(gvm.VISION_CACHE_FILE.read_text(encoding="utf-8"))
    assert on_disk["matches"][expected_key] == shots

    # analytics side effect also actually ran
    assert recorded.get("task") == "vision_match"
    assert recorded.get("metadata", {}).get("matched_shots") == 1


def test_match_script_to_video_parses_raw_json_without_markdown_fence(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "0")
    monkeypatch.setenv("DAILY_COST_THB_LIMIT", "0")
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "get_cached_matches", classmethod(lambda cls, p, c: None))
    monkeypatch.setattr(
        gvm.GeminiVisionMatcher, "get_or_upload_video",
        classmethod(lambda cls, client, path: MagicMock(name="remote_video")),
    )
    from scripts import token_tracker
    monkeypatch.setattr(token_tracker.TokenTracker, "record_event", lambda **kw: None)

    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"data")

    shots = [{"cue_id": 1, "start_time": 0.0, "end_time": 2.0}]
    resp = MagicMock()
    resp.text = json.dumps({"matched_shots": shots})  # no ```json fence at all
    factory = _fake_client_factory([resp])

    with patch("google.genai.Client", side_effect=factory):
        result = gvm.GeminiVisionMatcher.match_script_to_video(str(raw), _CUES, raw_duration=10.0)

    assert result == shots


def test_match_script_to_video_truncated_json_response_falls_back_gracefully(monkeypatch, tmp_path):
    """A truncated/malformed JSON body from the model must not crash the
    render -- match_script_to_video wraps the whole call in try/except and
    degrades to [] (or a prior cached match) rather than propagating
    json.JSONDecodeError up into the pipeline."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "0")
    monkeypatch.setenv("DAILY_COST_THB_LIMIT", "0")
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "get_cached_matches", classmethod(lambda cls, p, c: None))
    monkeypatch.setattr(
        gvm.GeminiVisionMatcher, "get_or_upload_video",
        classmethod(lambda cls, client, path: MagicMock(name="remote_video")),
    )

    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"data")

    resp = MagicMock()
    resp.text = "```json\n{\"matched_shots\": [truncated"
    factory = _fake_client_factory([resp])

    with patch("google.genai.Client", side_effect=factory):
        result = gvm.GeminiVisionMatcher.match_script_to_video(str(raw), _CUES, raw_duration=10.0)

    assert result == []
    # no cache entry written for the failed parse
    assert not gvm.VISION_CACHE_FILE.exists() or "matches" not in json.loads(
        gvm.VISION_CACHE_FILE.read_text(encoding="utf-8") or "{}"
    )


def _prime_failed_parse(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("DAILY_TOKEN_LIMIT", "0")
    monkeypatch.setenv("DAILY_COST_THB_LIMIT", "0")
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "get_cached_matches", classmethod(lambda cls, p, c: None))
    monkeypatch.setattr(
        gvm.GeminiVisionMatcher, "get_or_upload_video",
        classmethod(lambda cls, client, path: MagicMock(name="remote_video")),
    )


def test_a_failed_parse_does_not_reuse_a_match_from_a_different_script(monkeypatch, tmp_path):
    """A cached map for the same video but different cues must be ignored.

    The fallbacks used to scan for any key starting with the file hash --
    the video half of `{file_hash}_{md5(cue text)}` -- so after a script
    edit they returned shots timed to lines that no longer existed, with
    nothing to say the map was stale. Returning [] sends the render to
    rhythmic cuts instead, which is right for text nobody has analysed.
    """
    _prime_failed_parse(monkeypatch)

    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"data")
    file_hash = gvm.GeminiVisionMatcher._compute_file_hash(raw.resolve())
    stale_shots = [{"cue_id": 1, "start_time": 1.0, "end_time": 3.0}]
    gvm.GeminiVisionMatcher._save_cache({"matches": {f"{file_hash}_oldkey": stale_shots}})

    resp = MagicMock()
    resp.text = "not even json"
    with patch("google.genai.Client", side_effect=_fake_client_factory([resp])):
        result = gvm.GeminiVisionMatcher.match_script_to_video(str(raw), _CUES, raw_duration=10.0)

    assert result == []


def test_a_failed_parse_still_reuses_the_map_for_this_exact_script(monkeypatch, tmp_path):
    """The same-video-same-cues entry is still worth falling back to."""
    import hashlib

    _prime_failed_parse(monkeypatch)

    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"data")
    file_hash = gvm.GeminiVisionMatcher._compute_file_hash(raw.resolve())
    # Key it exactly as match_script_to_video does.
    cues_summary = "|".join([f"{c.get('text', '')}" for c in _CUES])
    exact_key = f"{file_hash}_{hashlib.md5(cues_summary.encode('utf-8')).hexdigest()}"
    shots = [{"cue_id": 1, "start_time": 1.0, "end_time": 3.0}]
    gvm.GeminiVisionMatcher._save_cache({"matches": {exact_key: shots}})

    resp = MagicMock()
    resp.text = "not even json"
    with patch("google.genai.Client", side_effect=_fake_client_factory([resp])):
        result = gvm.GeminiVisionMatcher.match_script_to_video(str(raw), _CUES, raw_duration=10.0)

    assert result == shots


def test_match_script_to_video_quota_error_is_never_caught_by_the_broad_except(monkeypatch, tmp_path):
    """check_budget() runs in the caller's control flow BEFORE the broad
    try/except -- confirm a quota AppError still propagates and is not
    swallowed into an empty-list fallback."""
    from scripts.error_handler import AppError, ErrorCategory
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setattr(gvm.GeminiVisionMatcher, "get_cached_matches", classmethod(lambda cls, p, c: None))

    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"data")

    quota_err = AppError(
        category=ErrorCategory.AI_PROVIDER, code="AI_QUOTA_EXCEEDED",
        message_th="เกิน", suggestion_th="รอ",
    )
    with patch("scripts.quota.check_budget", side_effect=quota_err):
        with pytest.raises(AppError):
            gvm.GeminiVisionMatcher.match_script_to_video(str(raw), _CUES, raw_duration=10.0)
