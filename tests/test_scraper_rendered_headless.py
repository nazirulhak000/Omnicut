"""Browser scrape never opens a visible window for API callers and is
serialised on the shared Chrome profile (audit S1-15). Playwright is faked."""

import sys
import threading
import time
import types

import scripts.product_scraper as scraper_module


class _FakeLocator:
    def __init__(self, text):
        self._text = text

    def inner_text(self, timeout=None):
        return self._text


class _FakePage:
    url = "https://shop.tiktok.com/th/pdp/1"

    def __init__(self, body):
        self._body = body

    def wait_for_timeout(self, _ms):
        pass

    def evaluate(self, _script):
        return ""

    def locator(self, _selector):
        return _FakeLocator(self._body)

    def content(self):
        return "<html></html>"

    def goto(self, *_a, **_k):
        pass


class _FakeContext:
    def __init__(self, body):
        self.pages = [_FakePage(body)]

    def add_init_script(self, _script):
        pass

    def new_page(self):
        return self.pages[0]

    def close(self):
        pass


def _install_fake_playwright(monkeypatch, launches, body, profile_dir):
    class Chromium:
        def launch_persistent_context(self, _profile, **kwargs):
            launches.append(kwargs.get("headless"))
            return _FakeContext(body)

    class Playwright:
        chromium = Chromium()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = lambda: Playwright()
    package = types.ModuleType("playwright")
    package.sync_api = sync_api
    monkeypatch.setitem(sys.modules, "playwright", package)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)
    monkeypatch.setattr(scraper_module, "RENDERED_PROFILE_DIR", profile_dir)


def test_challenge_does_not_open_headed_browser_by_default(monkeypatch, tmp_path):
    launches = []
    _install_fake_playwright(monkeypatch, launches, "Verify to continue: drag the puzzle", tmp_path / "profile")

    result = scraper_module._scrape_rendered_page("https://shop.tiktok.com/th/pdp/1")

    assert launches == [True]  # headless only
    assert result.get("challenge") is True


def test_headed_retry_only_when_explicitly_allowed(monkeypatch, tmp_path):
    launches = []
    _install_fake_playwright(monkeypatch, launches, "Verify to continue: drag the puzzle", tmp_path / "profile")
    monkeypatch.setattr(scraper_module, "RENDERED_CHALLENGE_WAIT_SECONDS", 0)

    scraper_module._scrape_rendered_page("https://shop.tiktok.com/th/pdp/1", allow_headed=True)

    assert launches == [True, False]


def test_rendered_scrapes_are_serialised(monkeypatch):
    active = {"now": 0, "max": 0}
    guard = threading.Lock()

    def fake_unlocked(_url, allow_headed=False):
        with guard:
            active["now"] += 1
            active["max"] = max(active["max"], active["now"])
        time.sleep(0.05)
        with guard:
            active["now"] -= 1
        return {"warning": "x"}

    monkeypatch.setattr(scraper_module, "_scrape_rendered_page_unlocked", fake_unlocked)
    threads = [threading.Thread(target=scraper_module._scrape_rendered_page, args=("u",)) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert active["max"] == 1


def test_busy_profile_returns_thai_warning(monkeypatch):
    monkeypatch.setattr(scraper_module, "RENDERED_PROFILE_LOCK_WAIT_SECONDS", 0.01)
    scraper_module._RENDERED_PROFILE_LOCK.acquire()
    try:
        result = scraper_module._scrape_rendered_page("u")
    finally:
        scraper_module._RENDERED_PROFILE_LOCK.release()
    assert "browser" in result["warning"]
    assert "ลองใหม่" in result["warning"]
