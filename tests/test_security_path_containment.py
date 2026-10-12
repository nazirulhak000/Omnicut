"""
Regression tests for the P0.5 4c security fix: path containment checks used
`str(target).startswith(str(root))`, a string-prefix comparison rather than
real path containment. A sibling directory that merely shares the same
character prefix (e.g. `D:\\...\\Capcut_evil\\` against a root of
`D:\\...\\Capcut`) passes a startswith() check even though it is NOT inside
that root -- letting the same-origin, unauthenticated endpoints in
api_videos.py / api_covers.py / api_editor.py serve or delete files well
outside their intended folders.

Fix: replace with `Path.relative_to()` inside try/except ValueError, via a
shared `_is_contained(path, root)` helper in each module -- the same style
already used correctly elsewhere in api_videos.py (rename_video_file,
reassign_raw_video, batch_delete_raw_videos).

Isolated per .agents/rules/testing_standard.md rule 3 -- uses tmp_path
throughout, never touches real project directories.
"""
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.api_videos as api_videos_mod
import scripts.api_covers as api_covers_mod
import scripts.api_editor as api_editor_mod


def _make_sibling_prefix_dirs(tmp_path):
    """Builds `<tmp>/Capcut` (the real root) and `<tmp>/Capcut_evil` (a
    sibling directory that shares the same string prefix but is NOT
    contained within it) -- the exact shape of the exploit in the audit."""
    root = tmp_path / "Capcut"
    evil_sibling = tmp_path / "Capcut_evil"
    root.mkdir()
    evil_sibling.mkdir()
    return root, evil_sibling


# ---------------------------------------------------------------------------
# _is_contained() unit tests -- shared shape across all three modules
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mod", [api_videos_mod, api_covers_mod, api_editor_mod])
def test_is_contained_rejects_sibling_directory_with_shared_prefix(tmp_path, mod):
    root, evil_sibling = _make_sibling_prefix_dirs(tmp_path)
    secret_file = evil_sibling / "secrets.txt"
    secret_file.write_text("top secret")

    # This is exactly the case startswith() gets wrong: the sibling's path
    # string literally starts with the root's path string.
    assert str(secret_file).startswith(str(root)), "test setup must reproduce the shared-prefix condition"
    assert not mod._is_contained(secret_file, root)


@pytest.mark.parametrize("mod", [api_videos_mod, api_covers_mod, api_editor_mod])
def test_is_contained_accepts_real_descendant(tmp_path, mod):
    root, _ = _make_sibling_prefix_dirs(tmp_path)
    nested = root / "sub" / "file.mp4"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"x")
    assert mod._is_contained(nested, root)


@pytest.mark.parametrize("mod", [api_videos_mod, api_covers_mod, api_editor_mod])
def test_is_contained_accepts_root_itself(tmp_path, mod):
    root, _ = _make_sibling_prefix_dirs(tmp_path)
    assert mod._is_contained(root, root)


# ---------------------------------------------------------------------------
# api_covers.py / api_editor.py _resolve_media() -- filmstrip/cover endpoints
# named in the audit (api_covers.py:60, api_editor.py:45)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mod", [api_covers_mod, api_editor_mod])
def test_resolve_media_rejects_sibling_prefix_escape(tmp_path, monkeypatch, mod):
    root, evil_sibling = _make_sibling_prefix_dirs(tmp_path)
    capcut_draft = tmp_path / "CapCutDrafts"
    capcut_draft.mkdir()
    monkeypatch.setattr(mod, "BASE_DIR", root)
    monkeypatch.setattr(mod, "CAPCUT_DRAFT_DIR", capcut_draft)

    leaked_file = evil_sibling / "leaked.mp4"
    leaked_file.write_bytes(b"not yours")

    with pytest.raises(HTTPException) as exc_info:
        mod._resolve_media(str(leaked_file))
    assert exc_info.value.status_code == 403


@pytest.mark.parametrize("mod", [api_covers_mod, api_editor_mod])
def test_resolve_media_still_serves_legit_file_under_base_dir(tmp_path, monkeypatch, mod):
    root, _ = _make_sibling_prefix_dirs(tmp_path)
    capcut_draft = tmp_path / "CapCutDrafts"
    capcut_draft.mkdir()
    monkeypatch.setattr(mod, "BASE_DIR", root)
    monkeypatch.setattr(mod, "CAPCUT_DRAFT_DIR", capcut_draft)

    legit = root / "01_Raw" / "clip.mp4"
    legit.parent.mkdir(parents=True)
    legit.write_bytes(b"real clip")

    resolved = mod._resolve_media(str(legit))
    assert resolved == legit.resolve()


@pytest.mark.parametrize("mod", [api_covers_mod, api_editor_mod])
def test_resolve_media_still_serves_legit_file_under_capcut_draft_dir(tmp_path, monkeypatch, mod):
    root, _ = _make_sibling_prefix_dirs(tmp_path)
    capcut_draft = tmp_path / "CapCutDrafts"
    capcut_draft.mkdir()
    monkeypatch.setattr(mod, "BASE_DIR", root)
    monkeypatch.setattr(mod, "CAPCUT_DRAFT_DIR", capcut_draft)

    legit = capcut_draft / "draft123" / "preview.mp4"
    legit.parent.mkdir(parents=True)
    legit.write_bytes(b"draft preview")

    resolved = mod._resolve_media(str(legit))
    assert resolved == legit.resolve()


# ---------------------------------------------------------------------------
# api_videos.py -- reveal-file, delete-file, stream_media all used the same
# broken startswith() pattern (named: api_videos.py:508, 545 in the audit;
# stream_media at ~623 has the identical pattern and was fixed for
# consistency with the two named sites)
# ---------------------------------------------------------------------------

def test_reveal_file_rejects_sibling_prefix_escape(tmp_path, monkeypatch):
    root, evil_sibling = _make_sibling_prefix_dirs(tmp_path)
    monkeypatch.setattr(api_videos_mod, "BASE_DIR", root)

    exports_dir = root / "04_Exports"
    exports_dir.mkdir()

    evil_export_lookalike = tmp_path / "Capcut_evil" / "04_Exports"
    evil_export_lookalike.mkdir(parents=True)
    leaked = evil_export_lookalike / "leaked.mp4"
    leaked.write_bytes(b"not yours")

    req = api_videos_mod.RevealFileRequest(file_path=str(leaked))
    with pytest.raises(HTTPException) as exc_info:
        api_videos_mod.reveal_file(req)
    assert exc_info.value.status_code == 403


def test_reveal_file_still_works_for_legit_export(tmp_path, monkeypatch):
    root, _ = _make_sibling_prefix_dirs(tmp_path)
    monkeypatch.setattr(api_videos_mod, "BASE_DIR", root)
    monkeypatch.setattr(api_videos_mod, "os", api_videos_mod.os)  # no-op, keep os.name check real

    exports_dir = root / "04_Exports"
    exports_dir.mkdir()
    legit_file = exports_dir / "final_cut.mp4"
    legit_file.write_bytes(b"real export")

    req = api_videos_mod.RevealFileRequest(file_path=str(legit_file))
    if api_videos_mod.os.name != "nt":
        result = api_videos_mod.reveal_file(req)
        assert result == {"success": False, "message": "Not on Windows"}
    else:
        # Avoid actually spawning explorer.exe in CI/test runs.
        monkeypatch.setattr(
            api_videos_mod.subprocess, "Popen", lambda *a, **k: None
        )
        result = api_videos_mod.reveal_file(req)
        assert result["success"] is True


def test_delete_file_rejects_sibling_prefix_escape(tmp_path, monkeypatch):
    root, _ = _make_sibling_prefix_dirs(tmp_path)
    monkeypatch.setattr(api_videos_mod, "BASE_DIR", root)

    inbox = root / "00_Inbox"
    inbox.mkdir()

    evil_inbox_lookalike = tmp_path / "Capcut_evil" / "00_Inbox"
    evil_inbox_lookalike.mkdir(parents=True)
    leaked = evil_inbox_lookalike / "not_yours.mp4"
    leaked.write_bytes(b"data")

    from scripts.api_schemas import DeleteFileRequest
    req = DeleteFileRequest(file_path=str(leaked))
    with pytest.raises(HTTPException) as exc_info:
        api_videos_mod.delete_file(req)
    assert exc_info.value.status_code == 403
    # Must not have been deleted -- the request should be rejected before
    # any filesystem mutation.
    assert leaked.exists()


def test_delete_file_still_works_for_legit_inbox_file(tmp_path, monkeypatch):
    root, _ = _make_sibling_prefix_dirs(tmp_path)
    monkeypatch.setattr(api_videos_mod, "BASE_DIR", root)

    inbox = root / "00_Inbox"
    inbox.mkdir()
    legit_file = inbox / "clip.mp4"
    legit_file.write_bytes(b"data")

    from scripts.api_schemas import DeleteFileRequest
    req = DeleteFileRequest(file_path=str(legit_file))
    result = api_videos_mod.delete_file(req)
    assert result["success"] is True
    assert not legit_file.exists()


def test_stream_media_rejects_sibling_prefix_escape(tmp_path, monkeypatch):
    root, evil_sibling = _make_sibling_prefix_dirs(tmp_path)
    capcut_draft = tmp_path / "CapCutDrafts"
    capcut_draft.mkdir()
    monkeypatch.setattr(api_videos_mod, "BASE_DIR", root)
    monkeypatch.setattr(api_videos_mod, "CAPCUT_DRAFT_DIR", capcut_draft)

    leaked = evil_sibling / "leaked.mp4"
    leaked.write_bytes(b"data")

    with pytest.raises(HTTPException) as exc_info:
        api_videos_mod.stream_media(str(leaked), request=None)
    assert exc_info.value.status_code == 403


def test_stream_media_rebases_foreign_machine_absolute_path(tmp_path, monkeypatch):
    root = tmp_path / "OmnicutApp"
    root.mkdir()
    raw_dir = root / "01_Raw" / "sample_folder"
    raw_dir.mkdir(parents=True)
    local_video = raw_dir / "clip.mp4"
    local_video.write_bytes(b"sample video bytes")

    monkeypatch.setattr(api_videos_mod, "BASE_DIR", root)
    monkeypatch.setattr(api_videos_mod, "CAPCUT_DRAFT_DIR", tmp_path / "CapCutDrafts")

    # Foreign path from laptop e.g. D:\Winona\Programmer\Capcut\01_Raw\sample_folder\clip.mp4
    foreign_path = r"D:\Winona\Programmer\Capcut\01_Raw\sample_folder\clip.mp4"

    from starlette.requests import Request
    req = Request({"type": "http", "headers": [], "query_string": b""})

    # Call stream_media directly
    response = api_videos_mod.stream_media(foreign_path, request=req)
    assert response.status_code == 200
    assert response.body == b"sample video bytes"
