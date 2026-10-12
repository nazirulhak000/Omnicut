import asyncio
import hashlib
import json

import pytest

from scripts.hyperframes_authoring import AuthoringError, CreativeJobStore, validate_inputs, verify_snapshot
from scripts.hyperframes_ai_provider import HyperframesAIProvider


HTML = '<html><head></head><body><div data-composition-id="main" data-width="1080" data-height="1920" data-duration="3"><section class="clip" data-start="0" data-duration="3">Saved brief</section></div></body></html>'


def fixture(tmp_path, *, transport=None, source_state=None, clock=None):
    jobs = CreativeJobStore(tmp_path, **({"clock": clock} if clock else {}))
    inputs = {"audio_mode": "silent", "duration_seconds": 3,
        "style_profile": {"id": "saved", "version": 1, "tokens": {"color": "#FFFFFF"}}, "brief": "Saved brief"}
    packet = validate_inputs(tmp_path, inputs)
    packet.update(source_snapshot={"title": "Source facts"}, channel_identity={"channel_id": "main"}, source_binding={"type": "standalone"})
    row = jobs.create("main", "project", 1, packet, expected_source_revision="source1")
    async def good(**kwargs):
        return {"text": json.dumps({"files": [{"path": "index.html", "content": HTML}]}),
            "usage": {"prompt_token_count": 31, "total_token_count": 72, "secret": "never persist"}}
    service = HyperframesAIProvider(tmp_path, jobs=jobs, transport=transport or good,
        source_state=source_state or (lambda row, owner: (1, "source1")), key_getter=lambda: ["test-key"])
    return jobs, row, service


def test_provider_submits_real_immutable_job_and_owner_metadata(tmp_path):
    jobs, row, service = fixture(tmp_path)
    async def run():
        started = await service.start(row["id"], "main", 0)
        assert started["status"] == "authoring"
        return await service.wait(row["id"], "main")
    finished = asyncio.run(run())
    assert finished["status"] == "submitted"
    assert verify_snapshot(finished["submitted_revision"])
    assert finished["checkpoint"]["usage"] == {"prompt_token_count": 31, "total_token_count": 72}
    entry = (tmp_path / finished["submitted_revision"]["revision_relative_path"] / "index.html").read_text(encoding="utf-8")
    assert '"channel_id": "main"' in entry
    assert '"project_id": "project"' in entry
    with pytest.raises(AuthoringError):
        jobs.get(row["id"], "second")


@pytest.mark.parametrize("options,code", [({"model": "untrusted"}, "provider_model_invalid"),
    ({"timeout_seconds": True}, "provider_timeout_invalid"), ({"timeout_seconds": 301}, "provider_timeout_invalid"),
    ({"max_output_tokens": 16385}, "provider_tokens_invalid")])
def test_invalid_config_does_not_claim_or_call(tmp_path, options, code):
    jobs, row, service = fixture(tmp_path)
    with pytest.raises(AuthoringError) as error:
        asyncio.run(service.start(row["id"], "main", 0, **options))
    assert error.value.code == code
    assert jobs.get(row["id"], "main")["status"] == "queued"


@pytest.mark.parametrize("payload,code", [
    ({"files": [{"path": "../store.json", "content": "bad"}]}, "provider_output_path_invalid"),
    ({"files": [{"path": "C:\\escaped.html", "content": "bad"}]}, "provider_output_path_invalid"),
    ({"files": [{"path": "assets/input_0.wav", "content": "fake"}]}, "provider_output_path_invalid"),
    ({"files": [{"path": "index.html", "content": HTML}], "channel_id": "second"}, "provider_output_invalid"),
    ({"files": [{"path": "index.html", "content": HTML.replace("1080", "1920")}]}, "provider_composition_invalid"),
    ({"files": [{"path": "index.html", "content": HTML.replace("</head>", '<script src="https://evil.invalid/a.js"></script></head>')}]}, "network_dependency"),
])
def test_provider_rejects_untrusted_response_before_acceptance(tmp_path, payload, code):
    async def response(**kwargs):
        return {"text": json.dumps(payload)}
    jobs, row, service = fixture(tmp_path, transport=response)
    async def run():
        await service.start(row["id"], "main", 0)
        return await service.wait(row["id"], "main")
    finished = asyncio.run(run())
    assert finished["status"] == "failed"
    assert finished["checkpoint"]["error_code"] == code
    assert "submitted_revision" not in finished
    assert not (tmp_path / "store.json").exists()


def test_cancel_fences_late_completion_and_external_session_can_resume(tmp_path):
    cancelled = []
    async def pending(**kwargs):
        try:
            await asyncio.sleep(100)
        finally:
            cancelled.append(True)
    jobs, row, service = fixture(tmp_path, transport=pending)
    async def run():
        await service.start(row["id"], "main", 0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        cancelled_row = await service.cancel(row["id"], "main")
        external = jobs.claim(row["id"], "main", "external_session", cancelled_row["generation"])
        assert external["executor_id"] == "external_session"
        return cancelled_row
    result = asyncio.run(run())
    assert result["status"] == "interrupted"
    assert cancelled == [True]
    assert not (tmp_path / row["work_path"] / "index.html").exists()


def test_source_revision_drift_cannot_write_composition(tmp_path):
    calls = []
    def current(row, owner):
        calls.append(True)
        return (1, "source1") if len(calls) == 1 else (2, "source2")
    jobs, row, service = fixture(tmp_path, source_state=current)
    async def run():
        await service.start(row["id"], "main", 0)
        return await service.wait(row["id"], "main")
    result = asyncio.run(run())
    assert result["status"] == "failed"
    assert result["checkpoint"]["error_code"] == "stale_base_revision"
    assert not (tmp_path / row["work_path"] / "index.html").exists()


def test_asset_hash_drift_before_start_never_claims(tmp_path):
    jobs, row, service = fixture(tmp_path)
    with jobs.table.scoped_mutate("main") as rows:
        rows[0]["input_packet"]["asset_hashes"] = {"voiceover_path": "wrong"}
    with pytest.raises(AuthoringError) as error:
        asyncio.run(service.start(row["id"], "main", 0))
    assert error.value.code == "provider_input_changed"
    assert jobs.get(row["id"], "main")["status"] == "queued"


def test_missing_key_capability_is_truthful_and_no_claim(tmp_path):
    jobs, row, service = fixture(tmp_path)
    service.key_getter = lambda: []
    assert service.capabilities()["status"] == "missing_key"
    assert service.capabilities()["live_verified"] is False
    with pytest.raises(AuthoringError) as error:
        asyncio.run(service.start(row["id"], "main", 0))
    assert error.value.code == "provider_missing_key"
    assert jobs.get(row["id"], "main")["generation"] == 0


def test_recovery_expired_provider_lease_never_calls_transport(tmp_path):
    now = [100.0]
    jobs, row, service = fixture(tmp_path, clock=lambda: now[0])
    claim = jobs.claim(row["id"], "main", "in_app_gemini_crashed", 0, lease_seconds=60)
    now[0] = 161
    assert service.recover("main") == [row["id"]]
    result = jobs.get(row["id"], "main")
    assert result["status"] == "interrupted"
    assert result["generation"] == claim["generation"] + 1
    assert service.recover("main") == []


def test_existing_external_work_is_preserved(tmp_path):
    jobs, row, service = fixture(tmp_path)
    work = tmp_path / row["work_path"]
    work.mkdir(parents=True)
    (work / "index.html").write_text("external work", encoding="utf-8")
    with pytest.raises(AuthoringError) as error:
        asyncio.run(service.start(row["id"], "main", 0))
    assert error.value.code == "provider_work_not_empty"
    assert (work / "index.html").read_text(encoding="utf-8") == "external work"


def test_provider_vendors_exact_audio_and_rejects_omission(tmp_path):
    jobs, row, service = fixture(tmp_path)
    voice = tmp_path / "02_Assets/voice.wav"
    voice.parent.mkdir(parents=True)
    voice.write_bytes(b"exact saved audio")
    inputs = row["input_packet"]["inputs"] | {"audio_mode": "narration", "voiceover_path": "02_Assets/voice.wav", "script": "Exact saved script"}
    with jobs.table.scoped_mutate("main") as rows:
        rows[0]["input_packet"].update(validate_inputs(tmp_path, inputs))
    async def audio(**kwargs):
        prompt = json.loads(kwargs["prompt"])
        assert prompt["assets"]["voiceover_path"]["sha256"] == hashlib.sha256(voice.read_bytes()).hexdigest()
        html = HTML.replace("</body>", '<audio src="assets/input_0.wav" data-start="0" data-duration="3" data-volume="1"></audio></body>')
        return {"text": json.dumps({"files": [{"path": "index.html", "content": html}]})}
    service.transport = audio
    async def run():
        await service.start(row["id"], "main", 0)
        return await service.wait(row["id"], "main")
    finished = asyncio.run(run())
    assert finished["status"] == "submitted"
    sealed = tmp_path / finished["submitted_revision"]["revision_relative_path"] / "assets/input_0.wav"
    assert sealed.read_bytes() == voice.read_bytes()
    with pytest.raises(AuthoringError) as error:
        service._output(json.dumps({"files": [{"path": "index.html", "content": HTML}]}), jobs.get(row["id"], "main"))
    assert error.value.code == "provider_audio_missing"


def test_generation_lease_loss_cancels_async_transport(tmp_path):
    stopped = []
    async def pending(**kwargs):
        try:
            await asyncio.sleep(100)
        finally:
            stopped.append(True)
    jobs, row, service = fixture(tmp_path, transport=pending)
    service.heartbeat_seconds = 0.001
    async def run():
        await service.start(row["id"], "main", 0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        with jobs.table.scoped_mutate("main") as rows:
            rows[0].update(executor_id="new_external_owner", generation=2, fence="new-fence")
        result = await service.wait(row["id"], "main")
        return result
    result = asyncio.run(run())
    assert stopped == [True]
    assert result["executor_id"] == "new_external_owner"
    assert result["status"] == "authoring"


def test_provider_exception_is_sanitized_and_tasks_released(tmp_path):
    async def failed(**kwargs):
        raise RuntimeError("secret key test-key and raw prompt")
    jobs, row, service = fixture(tmp_path, transport=failed)
    async def run():
        await service.start(row["id"], "main", 0)
        return await service.wait(row["id"], "main")
    result = asyncio.run(run())
    assert result["checkpoint"]["error_code"] == "provider_request_failed"
    assert "test-key" not in json.dumps(result)
    assert service.tasks == {}


def test_provider_does_not_overwrite_work_added_during_request(tmp_path):
    jobs, row, service = fixture(tmp_path)
    async def modified(**kwargs):
        work = tmp_path / row["work_path"]
        work.mkdir(parents=True)
        (work / "index.html").write_text("external saved work", encoding="utf-8")
        return {"text": json.dumps({"files": [{"path": "index.html", "content": HTML}]})}
    service.transport = modified
    async def run():
        await service.start(row["id"], "main", 0)
        return await service.wait(row["id"], "main")
    result = asyncio.run(run())
    assert result["checkpoint"]["error_code"] == "provider_work_not_empty"
    assert (tmp_path / row["work_path"] / "index.html").read_text(encoding="utf-8") == "external saved work"


def test_provider_caps_concurrent_paid_requests(tmp_path):
    async def pending(**kwargs):
        await asyncio.sleep(100)
    jobs, row, service = fixture(tmp_path, transport=pending)
    rows = [row] + [jobs.create("main", "project", 1, row["input_packet"], expected_source_revision="source1") for _ in range(2)]
    async def run():
        for item in rows[:2]:
            await service.start(item["id"], "main", 0)
        with pytest.raises(AuthoringError) as error:
            await service.start(rows[2]["id"], "main", 0)
        assert error.value.code == "provider_busy"
        for item in rows[:2]:
            await service.cancel(item["id"], "main")
    asyncio.run(run())
    assert jobs.get(rows[2]["id"], "main")["status"] == "queued"


def test_provider_timeout_is_durable_and_requires_explicit_retry(tmp_path):
    async def expired(**kwargs):
        raise asyncio.TimeoutError()
    jobs, row, service = fixture(tmp_path, transport=expired)
    async def run():
        await service.start(row["id"], "main", 0)
        return await service.wait(row["id"], "main")
    result = asyncio.run(run())
    assert result["status"] == "failed"
    assert result["checkpoint"]["error_code"] == "provider_timeout"
    assert result["generation"] == 2
    assert service.recover("main") == []


def test_stale_source_before_start_never_claims_or_calls(tmp_path):
    jobs, row, service = fixture(tmp_path, source_state=lambda row, owner: (1, "different"))
    with pytest.raises(AuthoringError) as error:
        asyncio.run(service.start(row["id"], "main", 0))
    assert error.value.code == "stale_base_revision"
    assert jobs.get(row["id"], "main")["status"] == "queued"


def test_dead_process_identity_recovers_before_lease_expiry(tmp_path):
    jobs, row, service = fixture(tmp_path)
    jobs.claim(row["id"], "main", "in_app_gemini_dead", 0, lease_seconds=60)
    with jobs.table.scoped_mutate("main") as rows:
        rows[0]["checkpoint"] = {"executor_pid": 999999, "executor_creation": "old-process"}
    assert service.recover("main", alive=lambda identity: False) == [row["id"]]
    assert jobs.get(row["id"], "main")["status"] == "interrupted"
