"""
Flow Multi-Account Pool & Auto-Failover Manager for Google Flow.
Manages Google account pool, tracks credit quotas, resolves multi-user Playwright URLs,
and handles auto-failover when credits deplete below threshold.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.config import BASE_DIR

logger = logging.getLogger("omnicut.flow_accounts")

DEFAULT_ACCOUNTS_FILE = BASE_DIR / "_Docs" / "flow_accounts.json"
CDP_PORT = int(os.environ.get("FLOW_MCP_CDP_PORT", 9333))
DEFAULT_CDP_URL = f"http://127.0.0.1:{CDP_PORT}"

DEFAULT_POOL_SCHEMA: Dict[str, Any] = {
    "active_account_id": "acc_1",
    "auto_failover": True,
    "min_failover_credits": 25,
    "accounts": [
        {
            "id": "acc_1",
            "name": "Google Pro #1",
            "email": "nazirulhak.000@gmail.com",
            "user_index": 0,
            "status": "active",
            "credits": 810,
            "plan": "pro",
        },
        {
            "id": "acc_2",
            "name": "Google Pro #2",
            "email": "Account 2",
            "user_index": 1,
            "status": "active",
            "credits": 1000,
            "plan": "pro",
        },
        {
            "id": "acc_3",
            "name": "Google Pro #3",
            "email": "Account 3",
            "user_index": 2,
            "status": "active",
            "credits": 1000,
            "plan": "pro",
        },
        {
            "id": "acc_4",
            "name": "Google Pro #4",
            "email": "Account 4",
            "user_index": 3,
            "status": "active",
            "credits": 1000,
            "plan": "pro",
        },
        {
            "id": "acc_5",
            "name": "Google Pro #5",
            "email": "Account 5",
            "user_index": 4,
            "status": "active",
            "credits": 1000,
            "plan": "pro",
        },
    ],
}


class FlowAccountManager:
    """Thread-safe manager for Google Flow multi-account pool."""

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or DEFAULT_ACCOUNTS_FILE
        self._lock = threading.Lock()
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        """Initializes accounts file with default 5-account schema if absent."""
        with self._lock:
            if not self.file_path.exists():
                self._save_unlocked(DEFAULT_POOL_SCHEMA)

    def _load_unlocked(self) -> Dict[str, Any]:
        """Loads data from file without acquiring lock."""
        if not self.file_path.exists():
            return json.loads(json.dumps(DEFAULT_POOL_SCHEMA))
        try:
            return json.loads(self.file_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Error loading flow accounts from {self.file_path}: {e}, using default.")
            return json.loads(json.dumps(DEFAULT_POOL_SCHEMA))

    def _save_unlocked(self, data: Dict[str, Any]) -> None:
        """Atomic write using temporary file replacement."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self.file_path.with_suffix(f".tmp.{uuid.uuid4().hex[:6]}")
        tmp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_file.replace(self.file_path)

    def load(self) -> Dict[str, Any]:
        """Returns current account pool state."""
        with self._lock:
            return self._load_unlocked()

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Returns all configured accounts in pool."""
        data = self.load()
        return data.get("accounts", [])

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Finds account by ID."""
        for acc in self.get_accounts():
            if acc.get("id") == account_id:
                return acc
        return None

    def get_active_account(self) -> Dict[str, Any]:
        """Returns active account. Falls back to first account if active ID is invalid."""
        data = self.load()
        active_id = data.get("active_account_id", "acc_1")
        accounts = data.get("accounts", [])
        for acc in accounts:
            if acc.get("id") == active_id:
                return acc
        if accounts:
            return accounts[0]
        return DEFAULT_POOL_SCHEMA["accounts"][0]

    def set_active_account(self, account_id: str) -> Dict[str, Any]:
        """Sets active account by ID."""
        with self._lock:
            data = self._load_unlocked()
            matched = None
            for acc in data.get("accounts", []):
                if acc.get("id") == account_id:
                    matched = acc
                    break

            if not matched:
                raise ValueError(f"Account ID '{account_id}' not found in pool.")

            data["active_account_id"] = account_id
            self._save_unlocked(data)
            logger.info(f"Switched active Google Flow account to {account_id} ({matched.get('name')})")
            return matched

    def update_account_credits(self, account_id: str, credits: int) -> Dict[str, Any]:
        """Updates remaining credit quota for an account."""
        with self._lock:
            data = self._load_unlocked()
            updated_acc = None
            for acc in data.get("accounts", []):
                if acc.get("id") == account_id:
                    acc["credits"] = max(0, int(credits))
                    updated_acc = acc
                    break

            if not updated_acc:
                raise ValueError(f"Account ID '{account_id}' not found in pool.")

            self._save_unlocked(data)
            logger.debug(f"Updated credits for account {account_id}: {credits}")
            return updated_acc

    def update_account(self, account_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates account metadata/label (name, email, plan, status, etc.)."""
        with self._lock:
            data = self._load_unlocked()
            target = None
            for acc in data.get("accounts", []):
                if acc.get("id") == account_id:
                    for k, v in updates.items():
                        if k not in ("id", "user_index"):  # Preserve identity and user index
                            acc[k] = v
                    target = acc
                    break

            if not target:
                raise ValueError(f"Account ID '{account_id}' not found in pool.")

            self._save_unlocked(data)
            logger.info(f"Updated metadata for account {account_id}: {updates}")
            return target

    def set_auto_failover(self, enabled: bool, min_credits: Optional[int] = None) -> bool:
        """Toggles auto-failover on or off, optionally updating failover credit threshold."""
        with self._lock:
            data = self._load_unlocked()
            data["auto_failover"] = bool(enabled)
            if min_credits is not None:
                data["min_failover_credits"] = max(1, int(min_credits))
            self._save_unlocked(data)
            logger.info(f"Set auto_failover to {enabled} (min_credits={data.get('min_failover_credits')})")
            return data["auto_failover"]

    def is_auto_failover_enabled(self) -> bool:
        """Returns True if auto failover is enabled."""
        return bool(self.load().get("auto_failover", True))

    def get_min_failover_credits(self) -> int:
        """Returns threshold for auto failover (default 25)."""
        return int(self.load().get("min_failover_credits", 25))

    def get_next_available_account(
        self,
        min_credits: int = 25,
        auto_switch: bool = True,
        force_switch: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Auto-Failover:
        If active account has credits >= min_credits and not force_switch, returns active account.
        Otherwise searches round-robin for the next account with credits >= min_credits.
        If found and auto_switch is True, activates that account and saves.
        Returns the next available account or None if entire pool is exhausted.
        """
        with self._lock:
            data = self._load_unlocked()
            accounts = data.get("accounts", [])
            if not accounts:
                return None

            active_id = data.get("active_account_id", accounts[0].get("id"))
            active_idx = 0
            for idx, acc in enumerate(accounts):
                if acc.get("id") == active_id:
                    active_idx = idx
                    break

            active_acc = accounts[active_idx]
            active_credits = active_acc.get("credits", 0)

            # If active account still has sufficient credits and force_switch is False, keep it
            if active_credits >= min_credits and not force_switch:
                return active_acc

            # Round-robin search for next account with >= min_credits and not disabled
            num_accounts = len(accounts)
            for i in range(1, num_accounts + 1):
                cand_idx = (active_idx + i) % num_accounts
                cand = accounts[cand_idx]
                if cand.get("status") != "disabled" and cand.get("credits", 0) >= min_credits:
                    if auto_switch:
                        data["active_account_id"] = cand.get("id")
                        self._save_unlocked(data)
                        logger.info(
                            f"Auto-Failover triggered: switched from {active_id} "
                            f"(credits: {active_credits}) to {cand.get('id')} (credits: {cand.get('credits')})"
                        )
                    return cand

            logger.warning(f"Auto-Failover: All accounts have < {min_credits} credits in pool!")
            return None

    def resolve_flow_url(
        self,
        user_index: Optional[int] = None,
        account_id: Optional[str] = None,
        path: str = "",
    ) -> str:
        """
        Resolves Google Flow URL with user index:
        e.g. https://flow.google.com/u/{user_index}/
        If user_index is not provided, resolves from account_id or current active account.
        """
        if user_index is None:
            if account_id:
                acc = self.get_account(account_id)
                user_index = acc.get("user_index", 0) if acc else 0
            else:
                active_acc = self.get_active_account()
                user_index = active_acc.get("user_index", 0)

        clean_path = path.lstrip("/")
        if clean_path:
            return f"https://flow.google.com/u/{user_index}/{clean_path}"
        return f"https://flow.google.com/u/{user_index}/"

    def get_total_pool_credits(self) -> int:
        """Calculates total remaining credits across all enabled accounts in pool."""
        accounts = self.get_accounts()
        return sum(acc.get("credits", 0) for acc in accounts if acc.get("status") != "disabled")

    def get_pool_summary(self) -> Dict[str, Any]:
        """Returns structured account pool summary for API and UI consumption."""
        data = self.load()
        active_acc = self.get_active_account()
        total_credits = self.get_total_pool_credits()
        accounts = data.get("accounts", [])
        linked_count = len([
            a for a in accounts
            if a.get("authenticated") or (a.get("email") and "@" in a.get("email", "") and a.get("status") == "active")
        ])
        return {
            "active_account_id": data.get("active_account_id", active_acc.get("id")),
            "active_account": active_acc,
            "total_pool_credits": total_credits,
            "total_accounts": len(accounts),
            "linked_accounts_count": linked_count,
            "auto_failover": data.get("auto_failover", True),
            "min_failover_credits": data.get("min_failover_credits", 25),
            "accounts": accounts,
        }

    def sync_active_account_with_chrome(self, cdp_url: str = DEFAULT_CDP_URL) -> Optional[Dict[str, Any]]:
        """Reads active account from Chrome CDP and syncs credits/email to active account in pool."""
        info = read_active_account_from_chrome(cdp_url=cdp_url)
        if not info:
            return None
        active_acc = self.get_active_account()
        active_id = active_acc["id"]
        updates: Dict[str, Any] = {}
        if info.get("email"):
            updates["email"] = info["email"]
        if info.get("credits") is not None:
            updates["credits"] = info["credits"]
        if info.get("plan"):
            updates["plan"] = info["plan"]
        if updates:
            return self.update_account(active_id, updates)
        return active_acc

    def switch_account_with_chrome(
        self,
        account_id: Optional[str] = None,
        user_index: Optional[int] = None,
        cdp_url: str = DEFAULT_CDP_URL,
    ) -> Dict[str, Any]:
        """
        Switches active account in pool and synchronizes with real Chrome session.
        If user_index is specified, navigates Chrome to https://flow.google.com/u/{user_index}/?hl=en.
        Reads updated email and credits, or reports needs_login: True if slot is unauthenticated.
        """
        target_acc = None
        if account_id:
            target_acc = self.get_account(account_id)
        elif user_index is not None:
            for acc in self.get_accounts():
                if acc.get("user_index") == user_index:
                    target_acc = acc
                    break

        if not target_acc:
            raise ValueError(f"Account with ID '{account_id}' or user_index '{user_index}' not found.")

        target_id = target_acc["id"]
        target_uindex = target_acc.get("user_index", 0)

        # Attempt Chrome CDP switch if reachable
        if is_chrome_cdp_reachable(cdp_url, timeout=1.0):
            chrome_res = switch_chrome_user_index(target_uindex, cdp_url=cdp_url)
            if chrome_res.get("needs_login"):
                self.update_account(target_id, {
                    "authenticated": False,
                    "status": "unlinked",
                    "email": "",
                    "credits": 0,
                    "plan": None,
                })
                return {
                    "ok": True,
                    "needs_login": True,
                    "active_account": self.get_active_account(),
                    "target_account": self.get_account(target_id),
                    "accounts": self.get_accounts(),
                    "total_pool_credits": self.get_total_pool_credits(),
                    "message": f"สล็อต {target_uindex} ({target_acc.get('name')}) ยังไม่ได้เข้าสู่ระบบ Google ใน Chrome กรุณากดปุ่มเชื่อมต่อใน Chrome ก่อนใช้งาน",
                }

            updates: Dict[str, Any] = {
                "authenticated": True,
                "status": "active",
            }
            if chrome_res.get("email"):
                updates["email"] = chrome_res["email"]
            if chrome_res.get("credits") is not None:
                updates["credits"] = chrome_res["credits"]
            if updates:
                self.update_account(target_id, updates)

        switched = self.set_active_account(target_id)
        return {
            "ok": True,
            "needs_login": False,
            "active_account": switched,
            "accounts": self.get_accounts(),
            "total_pool_credits": self.get_total_pool_credits(),
            "message": f"Switched to account {target_id} ({switched.get('name')})",
        }


def is_chrome_cdp_reachable(cdp_url: str = DEFAULT_CDP_URL, timeout: float = 1.0) -> bool:
    """Checks whether Chrome DevTools Protocol port is answering."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{cdp_url.rstrip('/')}/json/version", headers={"User-Agent": "OmniCut-FlowCDP"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def read_active_account_from_chrome(cdp_url: str = DEFAULT_CDP_URL, timeout: float = 8.0) -> Optional[Dict[str, Any]]:
    """
    Connects to Chrome via Playwright CDP (port 9333) and reads active account email,
    credits, and plan from the 'Account details' button panel in Google Flow.
    """
    if not is_chrome_cdp_reachable(cdp_url, timeout=1.5):
        logger.debug(f"Chrome CDP not reachable at {cdp_url}")
        return None

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(cdp_url)
            if not browser.contexts:
                return None
            context = browser.contexts[0]
            flow_page = None
            for pg in context.pages:
                if "flow.google.com" in pg.url or "labs.google" in pg.url:
                    flow_page = pg
                    break
            if not flow_page and context.pages:
                flow_page = context.pages[0]
            if not flow_page:
                return None

            btn = flow_page.get_by_role("button", name="Account details")
            if btn.count() == 0:
                logger.debug(f"Account details button not found on {flow_page.url}")
                return None

            btn.click()
            flow_page.wait_for_timeout(600)

            panes = flow_page.locator(".cdk-overlay-pane").all()
            if not panes:
                return None

            text = panes[0].inner_text()

            # Close panel
            close_btn = flow_page.get_by_role("button", name="Close account panel")
            if close_btn.count() > 0:
                close_btn.click()
            else:
                flow_page.keyboard.press("Escape")

            # Extract email
            email_match = re.search(r"[\w\.\+-]+@[\w\.-]+\.\w+", text)
            email = email_match.group(0) if email_match else ""

            # Extract credits
            credits_match = re.search(r"(\d+)\s+Google Flow credits", text)
            credits = int(credits_match.group(1)) if credits_match else None

            # Extract plan
            plan = "pro" if "PRO" in (btn.inner_text() or "").upper() else "free"

            return {
                "email": email,
                "credits": credits,
                "plan": plan,
                "url": flow_page.url,
            }
    except Exception as exc:
        logger.warning(f"Failed reading active account from Chrome: {exc}")
        return None


def switch_chrome_user_index(
    user_index: int,
    cdp_url: str = DEFAULT_CDP_URL,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Navigates the open Flow page in Chrome to https://flow.google.com/u/{user_index}/?hl=en!
    Checks if redirected or if user is logged into that slot.
    If logged in, reads new account's email and credits from the page.
    If user is not logged in to that slot yet, returns needs_login: True.
    """
    if not is_chrome_cdp_reachable(cdp_url, timeout=1.5):
        logger.debug(f"Chrome CDP not reachable at {cdp_url}")
        return {"ok": False, "error": f"Chrome CDP not reachable at {cdp_url}", "needs_login": False}

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(cdp_url)
            if not browser.contexts:
                return {"ok": False, "error": "No browser context found", "needs_login": False}
            context = browser.contexts[0]
            flow_page = None
            for pg in context.pages:
                if "flow.google.com" in pg.url or "labs.google" in pg.url:
                    flow_page = pg
                    break
            if not flow_page and context.pages:
                flow_page = context.pages[0]
            if not flow_page:
                return {"ok": False, "error": "No Flow page open in Chrome", "needs_login": False}

            target_url = f"https://flow.google.com/u/{user_index}/?hl=en"
            logger.info(f"Navigating Chrome Flow page to {target_url}...")
            flow_page.goto(target_url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
            flow_page.wait_for_timeout(1500)

            final_url = flow_page.url
            logger.info(f"Navigated to {final_url} for user_index {user_index}")

            needs_login = False
            if "accounts.google.com" in final_url:
                needs_login = True
            elif user_index > 0 and f"/u/{user_index}/" not in final_url:
                needs_login = True

            if needs_login:
                return {
                    "ok": True,
                    "user_index": user_index,
                    "final_url": final_url,
                    "needs_login": True,
                    "message": f"User index {user_index} is not signed in yet in Chrome.",
                }

            # If signed in, read account details
            btn = flow_page.get_by_role("button", name="Account details")
            email = None
            credits = None
            if btn.count() > 0:
                btn.click()
                flow_page.wait_for_timeout(500)
                panes = flow_page.locator(".cdk-overlay-pane").all()
                if panes:
                    text = panes[0].inner_text()
                    email_match = re.search(r"[\w\.\+-]+@[\w\.-]+\.\w+", text)
                    if email_match:
                        email = email_match.group(0)
                    credits_match = re.search(r"(\d+)\s+Google Flow credits", text)
                    if credits_match:
                        credits = int(credits_match.group(1))

                close_btn = flow_page.get_by_role("button", name="Close account panel")
                if close_btn.count() > 0:
                    close_btn.click()
                else:
                    flow_page.keyboard.press("Escape")

            return {
                "ok": True,
                "user_index": user_index,
                "final_url": final_url,
                "needs_login": False,
                "email": email,
                "credits": credits,
            }
    except Exception as exc:
        logger.error(f"Error switching Chrome user index: {exc}")
        return {"ok": False, "error": str(exc), "needs_login": False}


def launch_interactive_chrome(url: str = "https://accounts.google.com/AddSession?continue=https%3A%2F%2Fflow.google.com%2F") -> bool:
    """Launches Chrome with flow-mcp profile directly onto WinSta0\\Default so the user sees it."""
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    chrome_exe = None
    for p in chrome_paths:
        if os.path.exists(p):
            chrome_exe = p
            break
    if not chrome_exe:
        return False

    profile_dir = str(Path.home() / ".flow-mcp" / "chrome-profile")
    cmd = [
        chrome_exe,
        f"--user-data-dir={profile_dir}",
        f"--remote-debugging-port={CDP_PORT}",
        "--no-first-run",
        "--no-default-browser-check",
        url,
    ]
    startupinfo = None
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.lpDesktop = "WinSta0\\Default"

    try:
        subprocess.Popen(cmd, startupinfo=startupinfo)
        return True
    except Exception as e:
        logger.warning(f"Failed to launch Chrome on WinSta0\\Default: {e}")
        return False


def open_chrome_login(
    cdp_url: str = DEFAULT_CDP_URL,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Opens Google Chrome interactive window on the user's desktop with the Google Flow profile,
    navigating directly to the Add Account / Sign in page so the user can sign into all 5 accounts.
    """
    add_session_url = "https://accounts.google.com/AddSession?continue=https%3A%2F%2Fflow.google.com%2F"

    # 1. If CDP is answering, try to navigate the open page and bring to front
    navigated = False
    if is_chrome_cdp_reachable(cdp_url, timeout=1.5):
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(cdp_url)
                if browser.contexts:
                    context = browser.contexts[0]
                    flow_page = None
                    for pg in context.pages:
                        if "flow.google.com" in pg.url or "labs.google" in pg.url or "accounts.google.com" in pg.url:
                            flow_page = pg
                            break
                    if not flow_page and context.pages:
                        flow_page = context.pages[0]

                    if flow_page:
                        flow_page.goto(
                            add_session_url,
                            wait_until="domcontentloaded",
                            timeout=int(timeout * 1000),
                        )
                        flow_page.bring_to_front()
                        navigated = True
        except Exception as exc:
            logger.debug(f"Chrome CDP navigation notice: {exc}")

    # 2. Also ensure interactive Chrome is launched on WinSta0\\Default so the user sees it
    launched = launch_interactive_chrome(add_session_url)

    # 3. Also try os.startfile on the bat script as fallback
    bat_file = BASE_DIR / "tools" / "open_flow_login.bat"
    if os.name == "nt" and bat_file.exists():
        try:
            os.startfile(str(bat_file))
        except Exception:
            pass

    return {
        "ok": True,
        "message": "เปิดหน้าต่าง Google Chrome สำหรับเพิ่มบัญชีเรียบร้อยแล้ว",
        "navigated": navigated,
        "launched": launched,
    }


_manager_instance: Optional[FlowAccountManager] = None
_manager_lock = threading.Lock()


def get_flow_account_manager(file_path: Optional[Path] = None) -> FlowAccountManager:
    """Returns singleton instance of FlowAccountManager."""
    global _manager_instance
    with _manager_lock:
        if _manager_instance is None or file_path is not None:
            _manager_instance = FlowAccountManager(file_path=file_path)
        return _manager_instance
