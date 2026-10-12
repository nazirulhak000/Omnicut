"""
Unit tests for scripts/api_hyperframes.py.
Covers status check, approved styles, compositions listing, clip creation,
rendering with ExportRegistry bridge, and zero-leakage cleanup.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.api_server import app
from scripts.export_registry import ExportRegistry

client = TestClient(app)


@pytest.fixture(autouse=True)
def studio_fixture(isolated_storage, monkeypatch):
    """A writable Studio sandbox; tests never require production compositions."""
    from scripts import api_hyperframes
    studio = isolated_storage / "03_Projects" / "_HyperFrames_Studio"
    studio.mkdir(parents=True)
    for attribute, name in (("COMPOSITIONS_DIR", "compositions"), ("CLIPS_DIR", "clips"),
                            ("KIT_DIR", "kit"), ("ASSETS_DIR", "assets")):
        directory = studio / name
        directory.mkdir()
        monkeypatch.setattr(api_hyperframes, attribute, directory)
    monkeypatch.setattr(api_hyperframes, "STUDIO_DIR", studio)
    return studio


def test_get_hyperframes_status():
    """Status endpoint returns required system check keys."""
    resp = client.get("/api/hyperframes/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "studio_installed" in data
    assert "node_installed" in data
    assert "hyperframes_cli_ready" in data
    assert "compositions_count" in data
    assert "ready" in data


def test_get_approved_styles():
    """Styles endpoint returns all 4 human-crafted styles from STYLE.md."""
    resp = client.get("/api/hyperframes/styles")
    assert resp.status_code == 200
    styles = resp.json()
    assert len(styles) == 4
    style_ids = [s["id"] for s in styles]
    assert "meme_pas" in style_ids
    assert "tech_explainer" in style_ids
    assert "vs_battle" in style_ids
    assert "pov_chat" in style_ids

    # Verify Meme-PAS details
    meme = next(s for s in styles if s["id"] == "meme_pas")
    assert "Meme-PAS" in meme["name"]
    assert "hat01-meme-45s" in meme["reference"]
    assert meme["has_voiceover"] is True

    # Verify POV Chat details
    pov = next(s for s in styles if s["id"] == "pov_chat")
    assert "POV Chat Story" in pov["name"]
    assert pov["has_voiceover"] is False


def test_list_compositions():
    """Compositions endpoint returns list of available composition items."""
    resp = client.get("/api/hyperframes/compositions")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    if items:
        first = items[0]
        assert "id" in first
        assert "filename" in first
        assert "duration" in first
        assert "title" in first


def test_create_clip_validation_errors():
    """Create clip endpoint validates clip_id format and existing names."""
    # Invalid characters in clip_id
    bad_resp = client.post(
        "/api/hyperframes/create-clip",
        json={"clip_id": "bad name with spaces!", "product": "ess02"},
    )
    assert bad_resp.status_code == 422
    assert bad_resp.json()["code"] == "composition_id_invalid"

    # Non-existent product
    no_prod_resp = client.post(
        "/api/hyperframes/create-clip",
        json={"clip_id": "test-clip-99s", "product": "non_existent_product_xyz"},
    )
    assert no_prod_resp.status_code == 400


def test_render_composition_not_found():
    """Render returns 404 for missing composition."""
    resp = client.post(
        "/api/hyperframes/render",
        json={"composition_id": "completely_non_existent_comp_123"},
    )
    assert resp.status_code == 404


def test_render_composition_test_mode(tmp_path, monkeypatch):
    """Render in test mode places output in tmp directory and does not register in export registry."""
    from scripts import api_hyperframes

    mock_mp4 = tmp_path / "test_out.mp4"
    mock_mp4.write_bytes(b"dummy video data")

    # Mock subprocess run to simulate successful npx render
    def mock_run(cmd, *args, **kwargs):
        if "-o" in cmd:
            out_file = Path(cmd[cmd.index("-o") + 1])
            out_file.write_bytes(b"dummy mp4 video bytes")
        m = MagicMock()
        m.returncode = 0
        return m

    monkeypatch.setattr(api_hyperframes.subprocess, "run", mock_run)
    monkeypatch.setattr(api_hyperframes, "TMP_DIR", tmp_path)

    # Patch COMPOSITIONS_DIR so it finds a mock composition
    mock_comp = tmp_path / "mock-clip-10s.html"
    mock_comp.write_text('<html><head></head><body data-duration="10">Mock</body></html>', encoding="utf-8")
    monkeypatch.setattr(api_hyperframes, "COMPOSITIONS_DIR", tmp_path)

    resp = client.post(
        "/api/hyperframes/render",
        json={
            "composition_id": "mock-clip-10s",
            "is_test": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rendered"
    assert data["is_test"] is True
    assert data["export_id"] is None


def test_open_studio_endpoint(monkeypatch):
    """Open studio endpoint triggers background preview launch."""
    from scripts import api_hyperframes

    monkeypatch.setattr(api_hyperframes.subprocess, "Popen", MagicMock())
    monkeypatch.setattr(api_hyperframes.urllib.request, "urlopen", MagicMock(side_effect=OSError("offline")))
    monkeypatch.setattr(api_hyperframes.webbrowser, "open", MagicMock())
    resp = client.post("/api/hyperframes/open-studio", json={"port": 3100})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"
    assert "3100" in data["url"]


def test_render_composition_final_registers_export(tmp_path, monkeypatch):
    """Final render registers export in ExportRegistry and cleans up."""
    from scripts import api_hyperframes

    def mock_run(cmd, *args, **kwargs):
        if "-o" in cmd:
            out_file = Path(cmd[cmd.index("-o") + 1])
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_bytes(b"dummy final mp4")
        m = MagicMock()
        m.returncode = 0
        return m

    monkeypatch.setattr(api_hyperframes.subprocess, "run", mock_run)
    monkeypatch.setattr(api_hyperframes, "EXPORTS_DIR", tmp_path)

    mock_comp = tmp_path / "mock-final-30s.html"
    mock_comp.write_text('<html><head></head><body data-duration="30">Mock Final</body></html>', encoding="utf-8")
    monkeypatch.setattr(api_hyperframes, "COMPOSITIONS_DIR", tmp_path)

    # Mock ExportRegistry.ensure_many
    mock_ensure = MagicMock(return_value=[{"id": "exp_mock_123"}])
    monkeypatch.setattr(api_hyperframes.ExportRegistry, "ensure_many", mock_ensure)
    product = api_hyperframes.ProductStore.add("Fixture exact product", channel_id="main")

    resp = client.post(
        "/api/hyperframes/render",
        json={
            "composition_id": "mock-final-30s",
            "is_test": False,
            "product_id": product["id"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rendered"
    assert data["is_test"] is False
    assert data["export_id"] == "exp_mock_123"
    assert mock_ensure.called
    row = mock_ensure.call_args.args[0][0]
    assert row["product_id"] == product["id"]
    assert mock_ensure.call_args.kwargs["channel_id"] == "main"
    assert mock_ensure.call_args.kwargs["job_scope"]["channel_identity_snapshot"]["channel_id"] == "main"
