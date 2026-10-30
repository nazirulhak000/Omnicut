"""Offline checks for the Colab runner notebook generator (scripts/build_colab_notebook.py)."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from scripts import build_colab_notebook as builder

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKEN_PREFIX = "eyJhIjoi"  # base64 of '{"a":"' — every Cloudflare tunnel token starts with it


def _code_cells(nb: dict) -> list[str]:
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("colab_nb") / "runner.ipynb"
    path = builder.generate_notebook(out)
    assert path == out
    nb = json.loads(out.read_text(encoding="utf-8"))
    return out, nb


def test_notebook_is_valid_json_with_expected_cells(built):
    _, nb = built
    assert nb["nbformat"] == 4
    codes = _code_cells(nb)
    assert len(codes) >= 2
    assert "run_login_flow()" in codes[1]


def test_every_code_cell_compiles(built):
    _, nb = built
    for i, src in enumerate(_code_cells(nb)):
        compile(src, f"<cell {i}>", "exec")


def test_no_tunnel_token_literal_anywhere(built):
    out, _ = built
    assert TOKEN_PREFIX not in out.read_text(encoding="utf-8")
    assert TOKEN_PREFIX not in (REPO_ROOT / "scripts" / "build_colab_notebook.py").read_text(encoding="utf-8")


def test_committed_notebook_has_no_token_literal_and_matches_builder():
    committed = REPO_ROOT / "Omnicut_Cloud_Runner.ipynb"
    text = committed.read_text(encoding="utf-8")
    assert TOKEN_PREFIX not in text
    assert json.loads(text) == builder.build_notebook(), "regenerate: python scripts/build_colab_notebook.py"


def test_tunnel_token_form_field_defaults_empty_and_reads_secrets(built):
    runner = _code_cells(built[1])[0]
    assert 'CLOUDFLARE_TUNNEL_TOKEN = ""  # @param {type:"string"}' in runner
    assert "_colab_secret('CLOUDFLARE_TUNNEL_TOKEN')" in runner
    assert "cloudflare_tunnel_token" in runner
    assert "trycloudflare" in runner
    # token goes through env, never on the command line
    assert "'--token'" not in runner
    assert "tunnel_env['TUNNEL_TOKEN']" in runner


def test_allow_remote_bypass_removed(built):
    out, _ = built
    assert "OMNICUT_ALLOW_REMOTE" not in out.read_text(encoding="utf-8")
    assert "OMNICUT_ALLOW_REMOTE" not in (REPO_ROOT / "scripts" / "build_colab_notebook.py").read_text(encoding="utf-8")


def test_app_password_and_session_secret_passed_to_backend(built):
    runner = _code_cells(built[1])[0]
    assert "'OMNICUT_APP_PASSWORD'" in runner
    assert "api_env['OMNICUT_APP_PASSWORD'] = APP_PASSWORD" in runner
    assert "api_env['OMNICUT_SESSION_SECRET'] = SESSION_SECRET" in runner
    assert "/root/.omnicut_app_password" in runner
    assert "0o600" in runner
    assert "OMNICUT_APP_PASSWORD" in "".join(built[1]["cells"][0]["source"])  # owner instructions
    # the session secret value is never printed
    assert "print(SESSION_SECRET" not in runner and "{SESSION_SECRET}" not in runner


def test_ttyd_loopback_tmux_no_bash_fallback(built):
    runner = _code_cells(built[1])[0]
    tree = ast.parse(runner)
    ttyd_cmd = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "TTYD_CMD" for t in node.targets):
            ttyd_cmd = ast.unparse(node.value)
    assert ttyd_cmd is not None
    assert "'-i', 'lo'" in ttyd_cmd
    assert "'-W'" in ttyd_cmd
    assert "fontSize=15" in ttyd_cmd and "disableLeaveAlert=true" in ttyd_cmd
    assert "'tmux', 'new', '-A', '-s', 'agy'" in ttyd_cmd
    assert "|| bash" not in runner


def test_runner_cell_does_not_block_and_supervisor_runs_in_thread(built):
    runner = _code_cells(built[1])[0]
    tree = ast.parse(runner)
    top_level_whiles = [n for n in tree.body if isinstance(n, ast.While)]
    assert not top_level_whiles, "Cell 1 must finish so the login cell can run"
    assert "while True" not in runner
    assert "threading.Thread(target=_supervise" in runner
    for svc in ("'fastapi'", "'ttyd'", "'cloudflared'"):
        assert f"_register({svc}" in runner


def test_git_update_does_not_discard_local_changes(built):
    runner = _code_cells(built[1])[0]
    assert "'status', '--porcelain'" in runner
    assert "elif _dirty:" in runner
    assert "&& git reset -q --hard origin/main" not in runner
