"""
Unit and Integration Tests for Google Flow Multi-Account Pool & Auto-Failover.
Tests FlowAccountManager, API endpoints (/api/flow/accounts/*), and FlowService batch generation failover.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from starlette.testclient import TestClient

from scripts.flow_accounts import FlowAccountManager, DEFAULT_POOL_SCHEMA
from scripts.flow_service import FlowService, FlowJobStore
from scripts.api_server import app


@pytest.fixture
def test_accounts_file(tmp_path):
    accounts_file = tmp_path / "flow_accounts.json"
    return accounts_file


@pytest.fixture
def account_manager(test_accounts_file):
    return FlowAccountManager(file_path=test_accounts_file)


@pytest.fixture
def client():
    return TestClient(app)


def test_manager_initialization_defaults(account_manager):
    """Verifies that 5 Google accounts are initialized with correct schema."""
    accounts = account_manager.get_accounts()
    assert len(accounts) == 5
    assert accounts[0]["id"] == "acc_1"
    assert accounts[0]["user_index"] == 0
    assert accounts[4]["id"] == "acc_5"
    assert accounts[4]["user_index"] == 4

    active = account_manager.get_active_account()
    assert active["id"] == "acc_1"
    assert active["email"] == "nazirulhak.000@gmail.com"
    assert active["credits"] == 810
    assert account_manager.get_total_pool_credits() == 4810
    assert account_manager.is_auto_failover_enabled() is True
    assert account_manager.get_min_failover_credits() == 25


def test_switch_and_update_accounts(account_manager):
    """Tests switching active account and updating metadata/credits."""
    # Switch to acc_3
    switched = account_manager.set_active_account("acc_3")
    assert switched["id"] == "acc_3"
    assert account_manager.get_active_account()["id"] == "acc_3"

    # Invalid account ID raises ValueError
    with pytest.raises(ValueError):
        account_manager.set_active_account("invalid_acc_id")

    # Update credits for acc_3
    updated_acc = account_manager.update_account_credits("acc_3", 750)
    assert updated_acc["credits"] == 750
    assert account_manager.get_account("acc_3")["credits"] == 750

    # Update metadata
    updated_meta = account_manager.update_account("acc_3", {"name": "Work Pro Account", "email": "work@google.com"})
    assert updated_meta["name"] == "Work Pro Account"
    assert updated_meta["email"] == "work@google.com"
    # User index and ID remain preserved
    assert updated_meta["user_index"] == 2
    assert updated_meta["id"] == "acc_3"


def test_resolve_flow_url(account_manager):
    """Tests resolving Google Flow URL with /u/{user_index}/."""
    account_manager.set_active_account("acc_1")  # user_index = 0
    url_active = account_manager.resolve_flow_url()
    assert url_active == "https://flow.google.com/u/0/"

    # By account_id
    url_acc4 = account_manager.resolve_flow_url(account_id="acc_4")
    assert url_acc4 == "https://flow.google.com/u/3/"

    # With user_index explicit and path
    url_custom = account_manager.resolve_flow_url(user_index=2, path="project/12345")
    assert url_custom == "https://flow.google.com/u/2/project/12345"


def test_auto_failover_logic(account_manager):
    """Tests auto-failover when active account credits fall below threshold."""
    account_manager.set_active_account("acc_1")
    # Set acc_1 credits below min_credits (25)
    account_manager.update_account_credits("acc_1", 10)
    # Acc 2 has 1000 credits
    next_acc = account_manager.get_next_available_account(min_credits=25, auto_switch=True)
    assert next_acc is not None
    assert next_acc["id"] == "acc_2"
    assert account_manager.get_active_account()["id"] == "acc_2"

    # If acc_2 has enough credits, it stays on acc_2
    same_acc = account_manager.get_next_available_account(min_credits=25)
    assert same_acc["id"] == "acc_2"

    # Deplete all accounts
    for acc in account_manager.get_accounts():
        account_manager.update_account_credits(acc["id"], 5)

    exhausted = account_manager.get_next_available_account(min_credits=25)
    assert exhausted is None


def test_toggle_auto_failover(account_manager):
    """Tests toggling auto-failover and updating threshold."""
    state = account_manager.set_auto_failover(enabled=False, min_credits=50)
    assert state is False
    assert account_manager.is_auto_failover_enabled() is False
    assert account_manager.get_min_failover_credits() == 50

    account_manager.set_auto_failover(enabled=True)
    assert account_manager.is_auto_failover_enabled() is True


def test_api_accounts_endpoints(client, tmp_path, monkeypatch):
    """Tests /api/flow/accounts REST endpoints."""
    test_file = tmp_path / "api_test_flow_accounts.json"
    manager = FlowAccountManager(file_path=test_file)
    monkeypatch.setattr("scripts.api_flow.get_flow_account_manager", lambda: manager)
    # Isolate offline from ambient Chrome CDP port 9333 during baseline endpoint test
    monkeypatch.setattr("scripts.flow_accounts.is_chrome_cdp_reachable", lambda *a, **kw: False)

    # 1. GET /api/flow/accounts
    res = client.get("/api/flow/accounts")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert len(data["accounts"]) == 5
    assert data["active_account_id"] == "acc_1"
    assert data["total_pool_credits"] == 4810
    assert data["accounts"][0]["email"] == "nazirulhak.000@gmail.com"
    assert data["accounts"][0]["credits"] == 810

    # 2. POST /api/flow/accounts/switch
    res_switch = client.post("/api/flow/accounts/switch", json={"account_id": "acc_2"})
    assert res_switch.status_code == 200
    assert res_switch.json()["active_account"]["id"] == "acc_2"

    # 3. POST /api/flow/accounts/update
    res_upd = client.post("/api/flow/accounts/update", json={
        "account_id": "acc_2",
        "name": "Updated Studio Pro",
        "credits": 880,
    })
    assert res_upd.status_code == 200
    assert res_upd.json()["account"]["name"] == "Updated Studio Pro"
    assert res_upd.json()["account"]["credits"] == 880

    # 4. POST /api/flow/accounts/auto-failover
    res_toggle = client.post("/api/flow/accounts/auto-failover", json={"enabled": False, "min_credits": 30})
    assert res_toggle.status_code == 200
    assert res_toggle.json()["auto_failover"] is False
    assert res_toggle.json()["min_failover_credits"] == 30


def test_flow_service_batch_auto_failover(tmp_path, monkeypatch):
    """
    Tests FlowService.dispatch_batch_generation Auto-Failover:
    When an account has insufficient credits (< 25), automatically switches accounts
    and submits without crashing the batch.
    """
    test_jobs_file = tmp_path / "flow_jobs.json"
    test_accounts_file = tmp_path / "flow_accounts.json"
    monkeypatch.setattr("scripts.flow_service.FLOW_JOBS_FILE", test_jobs_file)

    manager = FlowAccountManager(file_path=test_accounts_file)
    # Acc 1 has only 25 credits (enough for only 1 shot)
    manager.update_account_credits("acc_1", 25)
    # Acc 2 has 1000 credits
    manager.update_account_credits("acc_2", 1000)
    manager.set_active_account("acc_1")

    mock_client = MagicMock()
    mock_client.is_healthy.return_value = True
    mock_client.generate.side_effect = [
        {"job_ids": ["client_job_acc1"]},
        {"job_ids": ["client_job_acc2"]},
    ]

    service = FlowService(client=mock_client, account_manager=manager)

    shots = [
        {"prompt": "Shot 1 with orbit", "max_credits": 25, "reference_images": ["ref1.png"]},
        {"prompt": "Shot 2 with dolly in", "max_credits": 25, "reference_images": ["ref2.png"]},
    ]

    res = service.dispatch_batch_generation(
        product_id="prod_failover_test",
        shots=shots,
        project_name="FailoverProj",
        auto_bundle=False,
    )

    assert res["job"]["status"] == "queued"
    assert len(res["job"]["scenes"]) == 2
    # Verify both client job ids were collected from chunked generation
    assert "client_job_acc1" in res["job"]["client_job_ids"]
    assert "client_job_acc2" in res["job"]["client_job_ids"]
    # Acc 2 became active after failover
    assert manager.get_active_account()["id"] == "acc_2"


def test_flow_service_batch_auto_failover_start_below_threshold(tmp_path, monkeypatch):
    """
    Tests simulate batch failover:
    Verify that when Account 1 has 10 credits (< 25) and Account 2 has 1000 credits,
    the batch dispatcher routes to Account 2 seamlessly from the very first shot.
    """
    test_jobs_file = tmp_path / "flow_jobs.json"
    test_accounts_file = tmp_path / "flow_accounts.json"
    monkeypatch.setattr("scripts.flow_service.FLOW_JOBS_FILE", test_jobs_file)

    manager = FlowAccountManager(file_path=test_accounts_file)
    manager.update_account_credits("acc_1", 10)
    manager.update_account_credits("acc_2", 1000)
    manager.set_active_account("acc_1")
    assert manager.get_active_account()["id"] == "acc_1"
    assert manager.get_active_account()["credits"] == 10

    mock_client = MagicMock()
    mock_client.is_healthy.return_value = True
    mock_client.generate.return_value = {"job_ids": ["client_job_routed_to_acc2"]}

    service = FlowService(client=mock_client, account_manager=manager)

    shots = [
        {"prompt": "Shot 1 needing 25 credits", "max_credits": 25, "reference_images": ["ref1.png"]},
    ]

    res = service.dispatch_batch_generation(
        product_id="prod_immediate_failover",
        shots=shots,
        project_name="ImmediateFailoverProj",
        auto_bundle=False,
    )

    assert res["job"]["status"] == "queued"
    assert "client_job_routed_to_acc2" in res["job"]["client_job_ids"]
    # Verify that the active account seamlessly switched to acc_2
    assert manager.get_active_account()["id"] == "acc_2"
    # Verify client.generate was called with the scene
    assert mock_client.generate.call_count == 1


def test_switch_account_with_user_index_and_needs_login(client, tmp_path, monkeypatch):
    """
    Tests switching account using user_index:
    1. When Chrome slot is not logged in (needs_login=True).
    2. When Chrome slot is logged in (reads email and credits).
    """
    test_file = tmp_path / "test_switch_user_index.json"
    manager = FlowAccountManager(file_path=test_file)
    monkeypatch.setattr("scripts.api_flow.get_flow_account_manager", lambda: manager)

    # Mock Chrome CDP reachable
    monkeypatch.setattr("scripts.flow_accounts.is_chrome_cdp_reachable", lambda *a, **kw: True)

    # 1. Slot 1 (acc_2) needs login
    def mock_switch_slot_1(user_index, **kw):
        assert user_index == 1
        return {
            "ok": True,
            "user_index": 1,
            "final_url": "https://accounts.google.com/signin",
            "needs_login": True,
            "message": "User index 1 is not signed in yet in Chrome.",
        }

    monkeypatch.setattr("scripts.flow_accounts.switch_chrome_user_index", mock_switch_slot_1)

    res = client.post("/api/flow/accounts/switch", json={"user_index": 1})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["needs_login"] is True
    assert data["target_account"]["id"] == "acc_2"
    # Active account remains on acc_1 because slot 1 is not logged in
    assert data["active_account"]["id"] == "acc_1"

    # 2. Slot 0 (acc_1) is logged in with real credits 810
    def mock_switch_slot_0(user_index, **kw):
        assert user_index == 0
        return {
            "ok": True,
            "user_index": 0,
            "final_url": "https://flow.google.com/u/0/?hl=en",
            "needs_login": False,
            "email": "nazirulhak.000@gmail.com",
            "credits": 810,
        }

    monkeypatch.setattr("scripts.flow_accounts.switch_chrome_user_index", mock_switch_slot_0)

    res0 = client.post("/api/flow/accounts/switch", json={"user_index": 0})
    assert res0.status_code == 200
    data0 = res0.json()
    assert data0["ok"] is True
    assert data0["needs_login"] is False
    assert data0["active_account"]["id"] == "acc_1"
    assert data0["active_account"]["email"] == "nazirulhak.000@gmail.com"
    assert data0["active_account"]["credits"] == 810


def test_open_login_endpoint(client, monkeypatch):
    """Tests POST /api/flow/accounts/open-login."""
    def mock_open_chrome_login(**kw):
        return {
            "ok": True,
            "url": "https://accounts.google.com/AccountChooser?continue=https%3A%2F%2Fflow.google.com%2F",
            "message": "Opened Google Account Chooser in Chrome. Click 'Use another account' to sign in.",
        }

    monkeypatch.setattr("scripts.flow_accounts.open_chrome_login", mock_open_chrome_login)

    res = client.post("/api/flow/accounts/open-login")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "AccountChooser" in data["url"]


def test_bundle_angle_shots_flow_endpoint(client, tmp_path, monkeypatch):
    """
    Tests GET /api/flow/product/{product_id}/angles/{angle_id}/shots-flow:
    Verifies that the 5 script beats are bundled with synthesized prompts and reference images.
    """
    from scripts.flow_service import FlowService

    mock_product = {
        "id": "prod_bundle_test",
        "name": "Super Fast Charger 100W",
        "specs": {"power": "100W", "ports": "Type-C"},
        "angles": [
            {
                "angle_id": "ang_1",
                "angle_name": "Problem vs Solution",
                "script_lines": [
                    "ชาร์จช้า เครื่องร้อนจนน่ารำคาญใช่ไหม",
                    "ลองตัวนี้เลย ชาร์จเร็ว 100W สบายใจ",
                    "มีชิปควบคุมอุณหภูมิอัจฉริยะ ปลอดภัยสุดๆ",
                    "สายถักแน่นหนา ใช้งานได้ทั้งมือถือและโน้ตบุ๊ก",
                    "กดที่ตะกร้าซ้ายล่าง สั่งซื้อได้เลย",
                ],
            }
        ],
    }

    monkeypatch.setattr("scripts.product_store.ProductStore.get", lambda pid, **kw: mock_product if pid == "prod_bundle_test" else None)
    monkeypatch.setattr("scripts.flow_prompt_engine.find_best_product_image", lambda pid: None)
    monkeypatch.setattr("scripts.flow_prompt_engine.expand_prompt_with_gemini", lambda **kw: "Mock cinematic commercial shot 9:16")

    # 1. Direct Service Call
    service = FlowService()
    bundled = service.bundle_angle_shots_flow("prod_bundle_test", "ang_1")
    assert bundled["ok"] is True
    assert bundled["product_id"] == "prod_bundle_test"
    assert bundled["angle_id"] == "ang_1"
    assert len(bundled["shots"]) == 5
    assert bundled["total_shots"] == 5
    assert bundled["estimated_credits"] == 125
    assert bundled["shots"][0]["shot_label"] == "Shot 1: Hook & Attention"
    assert bundled["shots"][0]["technique"] == "reveal"
    assert bundled["shots"][2]["technique"] == "macro"
    assert bundled["shots"][3]["technique"] == "orbit"

    # 2. REST Endpoint Call
    res = client.get("/api/flow/product/prod_bundle_test/angles/ang_1/shots-flow")
    assert res.status_code == 200
    api_data = res.json()
    assert api_data["ok"] is True
    assert len(api_data["shots"]) == 5
    assert api_data["shots"][0]["aspect_ratio"] == "9:16"
    assert api_data["shots"][0]["duration"] == 8

    # 3. 404 for unknown product or angle
    res_404_prod = client.get("/api/flow/product/unknown_prod/angles/ang_1/shots-flow")
    assert res_404_prod.status_code == 404
    res_404_angle = client.get("/api/flow/product/prod_bundle_test/angles/unknown_ang/shots-flow")
    assert res_404_angle.status_code == 404

