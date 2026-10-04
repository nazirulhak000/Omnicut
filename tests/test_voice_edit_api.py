"""`voice_edit` through the project state API (round EDITOR-CUT-QUALITY-R3, lane RB).

PATCH /api/projects/{name}/state used to drop every undeclared field silently; the
voice cuts must (1) be declared, (2) validated with a Thai 422, (3) persisted next to
the post-cut `total_duration`, and (4) come back from GET /api/projects/{name}.
Manifests live in tmp_path; no real project is touched.
"""

import wave

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts import api_phase1, project_manifest, voice_cut_map
from scripts.project_manifest import ProjectManifest

NAME = "voice-edit-api"
URL = f"/api/projects/{NAME}"
STATE = f"{URL}/state"
DURATION = 6.0


def _write_wav(path, seconds):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * int(8000 * seconds))


def cut(start, end, cid="c1", **extra):
    return {"id": cid, "start": start, "end": end, **extra}


def edit(cuts, **source):
    return {"schema_version": 1, "source": {"duration": DURATION, **source}, "cuts": cuts}


@pytest.fixture
def api(tmp_path, monkeypatch):
    for module in (project_manifest, voice_cut_map):
        monkeypatch.setattr(module, "BASE_DIR", tmp_path)
    monkeypatch.setattr(project_manifest, "PROJECTS_DIR", tmp_path / "03_Projects")
    monkeypatch.setattr(api_phase1, "_project_origin", lambda name: (None, None, None))
    project_dir = tmp_path / "03_Projects" / NAME
    project_dir.mkdir(parents=True)
    voice = project_dir / "voiceover.wav"
    _write_wav(voice, DURATION)
    ProjectManifest.save(NAME, clip_list=[], total_duration=DURATION, cues=[{"start": 0, "end": 1, "text": "x"}],
                         artifacts={"voice_audio": {"path": str(voice)}})
    app = FastAPI()
    app.include_router(api_phase1.router)
    client = TestClient(app)
    client.voice = voice
    return client


def _save(client, **payload):
    return client.patch(STATE, json=payload)


# ---------------------------------------------------------------------------
# round trip
# ---------------------------------------------------------------------------

def test_the_request_model_keeps_voice_edit_instead_of_dropping_it():
    request = api_phase1.UpdateProjectStateRequest(voice_edit=edit([cut(2.0, 2.5)]))
    assert request.voice_edit["cuts"][0]["id"] == "c1"
    assert "voice_edit" in request.model_fields_set
    assert "voice_edit" not in api_phase1.UpdateProjectStateRequest().model_fields_set


def test_save_then_manifest_then_load_returns_the_voice_edit(api):
    response = _save(api, voice_edit=edit([cut(2.01, 2.49, reason="silence")]))
    assert response.status_code == 200, response.text
    body = response.json()

    # server stamped the fingerprint of the CURRENT voice file and snapped the cut to the grid
    stored = ProjectManifest.load(NAME)["voice_edit"]
    identity = voice_cut_map.voice_file_identity(api.voice)
    assert stored["schema_version"] == 1
    assert stored["source"]["duration"] == DURATION
    assert stored["source"]["size"] == identity["size"]
    assert stored["source"]["mtime_ns"] == identity["mtime_ns"]
    assert stored["source"]["path"].replace("\\", "/").endswith("03_Projects/voice-edit-api/voiceover.wav")
    assert stored["cuts"] == [cut(2.0, 2.5, reason="silence")]

    # manifest total_duration = post-cut length; source.duration keeps the file's real length
    assert ProjectManifest.load(NAME)["total_duration"] == pytest.approx(5.5)
    assert body["voice_edit"] == stored
    assert body["voice_edit_stale"] is False
    assert body["total_duration"] == pytest.approx(5.5)

    loaded = api.get(URL).json()
    assert loaded["voice_edit"] == stored
    assert loaded["total_duration"] == pytest.approx(5.5)
    assert "voice_edit_stale" not in loaded or loaded["voice_edit_stale"] is False
    assert loaded["_editor_revision"] == body["_editor_revision"]


def test_two_cuts_total_duration(api):
    assert _save(api, voice_edit=edit([cut(2.0, 2.5, "a"), cut(4.0, 4.2, "b")])).status_code == 200
    assert ProjectManifest.load(NAME)["total_duration"] == pytest.approx(6.0 - 0.7)


def test_overlapping_off_grid_cuts_that_touch_after_snapping_are_merged(api):
    assert _save(api, voice_edit=edit([cut(2.0, 2.5, "a"), cut(2.51, 3.0, "b")])).status_code == 200
    assert ProjectManifest.load(NAME)["voice_edit"]["cuts"] == [cut(2.0, 3.0, "a", reason="manual")]


def test_a_save_that_omits_voice_edit_keeps_it(api):
    _save(api, voice_edit=edit([cut(2.0, 2.5)]))
    before = ProjectManifest.load(NAME)

    response = _save(api, hook_label="new label")

    assert response.status_code == 200
    after = ProjectManifest.load(NAME)
    assert after["voice_edit"] == before["voice_edit"]
    assert after["total_duration"] == pytest.approx(5.5)
    assert after["hook_label"] == "new label"
    assert response.json()["voice_edit"] == before["voice_edit"]


@pytest.mark.parametrize("clearing", [None, {"cuts": []}, edit([])])
def test_null_or_empty_voice_edit_clears_it_and_restores_the_real_length(api, clearing):
    _save(api, voice_edit=edit([cut(2.0, 2.5)]))
    assert ProjectManifest.load(NAME)["total_duration"] == pytest.approx(5.5)

    response = _save(api, voice_edit=clearing)

    assert response.status_code == 200, response.text
    saved = ProjectManifest.load(NAME)
    assert saved["voice_edit"] is None
    assert saved["total_duration"] == DURATION
    assert saved["voice_edit_stale"] is False
    assert response.json()["voice_edit"] is None


def test_clearing_does_not_touch_a_total_duration_someone_else_changed(api):
    _save(api, voice_edit=edit([cut(2.0, 2.5)]))
    ProjectManifest.save(NAME, total_duration=4.0)                 # e.g. a render with another voice length
    _save(api, voice_edit=None)
    assert ProjectManifest.load(NAME)["total_duration"] == 4.0


def test_replacing_the_cuts_updates_the_total(api):
    _save(api, voice_edit=edit([cut(2.0, 2.5)]))
    _save(api, voice_edit=edit([cut(1.0, 2.0, "x")]))
    saved = ProjectManifest.load(NAME)
    assert saved["total_duration"] == pytest.approx(5.0)
    assert [c["id"] for c in saved["voice_edit"]["cuts"]] == ["x"]


def test_saving_new_cuts_clears_an_old_dropped_or_stale_notice(api):
    ProjectManifest.save(NAME, voice_edit_stale=True, voice_edit_notice={"kind": "dropped", "reason": "x"})
    _save(api, voice_edit=edit([cut(2.0, 2.5)]))
    saved = ProjectManifest.load(NAME)
    assert saved["voice_edit_stale"] is False
    assert saved["voice_edit_notice"] is None


def test_other_state_fields_still_save_alongside_voice_edit(api):
    response = _save(api, voice_edit=edit([cut(2.0, 2.5)]), hook_label="L", cues=[{"start": 0, "end": 1.0, "text": "kept"}])
    assert response.status_code == 200
    saved = ProjectManifest.load(NAME)
    assert saved["hook_label"] == "L" and saved["cues"][0]["text"] == "kept"
    assert saved["render_params"]["hook_label"] == "L"
    assert "voice_edit" not in saved["render_params"]               # top level only


def test_revision_guard_still_applies_with_voice_edit(api):
    revision = api.get(URL).json()["_editor_revision"]
    assert _save(api, base_revision=revision, voice_edit=edit([cut(2.0, 2.5)])).status_code == 200
    stale = _save(api, base_revision=revision, voice_edit=edit([cut(1.0, 1.5)]))
    assert stale.status_code == 409
    assert ProjectManifest.load(NAME)["voice_edit"]["cuts"][0]["start"] == 2.0


# ---------------------------------------------------------------------------
# validation -> 422 in Thai, nothing written
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload, fragment", [
    (edit([cut(2.0, 2.5, "a"), cut(2.2, 3.0, "b")]), "ซ้อนกับ"),
    (edit([cut(4.0, 4.5, "a"), cut(1.0, 1.5, "b")]), "เรียงตามเวลา"),
    (edit([cut(2.0, 2.5, "a"), cut(3.0, 3.5, "a")]), "ซ้ำ"),
    (edit([{"start": 2.0, "end": 2.5}]), "id"),
    (edit([cut(2.0, 9.0)]), "อยู่ในความยาว"),
    (edit([cut(-1.0, 1.0)]), "อยู่ในความยาว"),
    (edit([cut(3.0, 2.0)]), "end ต้องมากกว่า start"),
    (edit([cut(2.0, 2.01)]), "สั้นกว่า 1 เฟรม"),
    (edit([cut(0.0, 5.5)]), "ขั้นต่ำ"),
    (edit([cut("a", "b")]), "ตัวเลข"),
    ({**edit([cut(2.0, 2.5)]), "schema_version": 9}, "schema_version"),
    ({"source": {"duration": -1}, "cuts": [cut(2.0, 2.5)]}, "duration"),
    ({"cuts": [cut(2.0, 2.5)]}, "source"),
])
def test_invalid_voice_edit_is_a_422_with_a_thai_message_and_changes_nothing(api, payload, fragment):
    before = ProjectManifest.load(NAME)

    response = _save(api, voice_edit=payload, hook_label="must not be saved")

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail.startswith("ตัดเสียงพากย์ไม่ได้")
    assert fragment in detail
    assert ProjectManifest.load(NAME) == before                    # all-or-nothing, label not written either


def test_a_non_object_voice_edit_is_rejected_by_the_model_itself(api):
    assert _save(api, voice_edit=["cuts"]).status_code == 422
    assert _save(api, voice_edit="cuts").status_code == 422


def test_cuts_cannot_be_saved_for_a_project_without_a_voice_file(api):
    ProjectManifest.save(NAME, artifacts={"voice_audio": {"path": "03_Projects/voice-edit-api/missing.wav"}})
    response = _save(api, voice_edit=edit([cut(2.0, 2.5)]))
    assert response.status_code == 422
    assert "ไม่พบไฟล์เสียงพากย์" in response.json()["detail"]
    assert "voice_edit" not in ProjectManifest.load(NAME)


# ---------------------------------------------------------------------------
# stale cuts are stored but flagged, never applied
# ---------------------------------------------------------------------------

def test_a_source_that_is_not_the_current_file_is_stored_flagged_stale_and_leaves_the_total_alone(api):
    identity = voice_cut_map.voice_file_identity(api.voice)
    other = edit([cut(2.0, 2.5)], path="03_Projects/voice-edit-api/voiceover.wav",
                 size=identity["size"] + 1, mtime_ns=identity["mtime_ns"])

    response = _save(api, voice_edit=other)

    assert response.status_code == 200
    assert response.json()["voice_edit_stale"] is True
    saved = ProjectManifest.load(NAME)
    assert saved["voice_edit"]["source"]["size"] == identity["size"] + 1      # the client's fingerprint, not ours
    assert saved["voice_edit_stale"] is True
    assert saved["total_duration"] == DURATION                                 # cuts do not apply -> untouched


def test_replacing_the_voice_file_after_saving_makes_the_load_report_stale(api):
    _save(api, voice_edit=edit([cut(2.0, 2.5)]))
    assert api.get(URL).json().get("voice_edit_stale") in (None, False)

    _write_wav(api.voice, 7.5)                                                  # new take, same path

    loaded = api.get(URL).json()
    assert loaded["voice_edit_stale"] is True
    assert loaded["voice_edit_notice"]["kind"] == "stale"
    assert "ไม่ตรงกับตอนที่ตัด" in loaded["voice_edit_notice"]["reason"]
    assert loaded["voice_edit"]["cuts"]                                         # still there for the editor to show
    assert ProjectManifest.load(NAME).get("voice_edit_stale") in (None, False)  # computed on read, not persisted
