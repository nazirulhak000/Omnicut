"""Startup recovery must be explicit and controlled by FastAPI lifespan."""

import asyncio

from fastapi import FastAPI

import scripts.api_server as api_server


def test_imported_app_does_not_recover_until_lifespan_starts(monkeypatch):
    calls = []

    def recover_background():
        calls.append("background")
        return 2

    def recover_batch():
        calls.append("batch")
        return 3

    monkeypatch.setattr(api_server, "recover_background_isolation_tasks", recover_background)
    monkeypatch.setattr(api_server.BatchRenderManager, "recover_pending_batches", recover_batch)
    probe_app = FastAPI(lifespan=api_server.lifespan)

    # Constructing/importing an app must not touch durable worker state.
    assert calls == []

    async def exercise_lifespan():
        async with api_server.lifespan(probe_app):
            assert calls == ["background", "batch"]
            assert probe_app.state.startup_recovery == {
                "background_isolation": 2,
                "batch_render": 3,
                "hyperframes": {"interrupted": 0, "queued": 0, "finalizing": 0},
                "hyperframes_ai": {"interrupted": [], "errors": []},
            }

    asyncio.run(exercise_lifespan())


def test_startup_recovery_isolates_subsystem_failure(monkeypatch):
    def recover_background():
        raise RuntimeError("corrupt checkpoint")

    monkeypatch.setattr(api_server, "recover_background_isolation_tasks", recover_background)
    monkeypatch.setattr(
        api_server.BatchRenderManager,
        "recover_pending_batches",
        lambda: 4,
    )

    assert api_server.recover_startup_work() == {
        "background_isolation": 0,
        "batch_render": 4,
        "hyperframes": {"interrupted": 0, "queued": 0, "finalizing": 0},
        "hyperframes_ai": {"interrupted": [], "errors": []},
    }


def test_provider_recovery_failure_does_not_reset_render_recovery(monkeypatch):
    from scripts import hyperframes_ai_provider, hyperframes_recovery
    monkeypatch.setattr(api_server, "recover_background_isolation_tasks", lambda: 0)
    monkeypatch.setattr(api_server.BatchRenderManager, "recover_pending_batches", lambda: 0)
    monkeypatch.setattr(hyperframes_recovery, "recover_hyperframes_work", lambda root: {"counts": {"interrupted": 2, "queued": 1, "finalizing": 0}})
    def fail(root):
        raise RuntimeError("corrupt provider checkpoint")
    monkeypatch.setattr(hyperframes_ai_provider, "recover_provider_work", fail)
    result = api_server.recover_startup_work()
    assert result["hyperframes"]["interrupted"] == 2
    assert result["hyperframes"]["queued"] == 1
    assert result["hyperframes_ai"]["errors"] == [{"code": "provider_recovery_failed"}]
