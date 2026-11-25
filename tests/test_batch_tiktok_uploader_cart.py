"""Unit tests for tools/batch_tiktok_uploader.py cart name resolution (B2/C3)."""
import json
import re
from tools import batch_tiktok_uploader as uploader


def _make_eval_stub(eval_calls, *, modal_already_open=False):
    def fake_eval_js(js, tab_id=None):
        eval_calls.append(js)
        # Step 0: modal already open
        if "t === 'นำเสนอสินค้า' || t === 'Showcase'" in js and "product-selector-modal" in js:
            return modal_already_open
        # Step 1: click Add link
        if ".anchor-tag-container button" in js:
            return {"success": True}
        # Step 2: click Next on Add link
        if "t === 'ถัดไป' || t === 'Next'" in js and "product-tb-row" not in js and "TUXTabBar" not in js and "nextBtn" not in js:
            return {"success": True}
        # Step 3: Showcase tab active check
        if "itemTitle--active" in js:
            return True
        # Step 4: search product ID
        if "input[placeholder*=\"ค้นหา\"]" in js:
            return {"success": True, "found": True}
        # Step 5: select product row radio
        if "target_product_not_found" in js:
            return {"success": True, "checked": True, "nextEnabled": True}
        # Step 6: Next in product table
        if "buttons.reverse().find" in js:
            return {"success": True}
        # Step 7: Title Dialog
        if "const desired =" in js:
            return {"success": True}
        # Step 8: Verify product attached
        if "modalStillOpen" in js:
            return True
        return False

    return fake_eval_js


def test_attach_product_link_resolves_cart_name_without_shadowing(monkeypatch):
    eval_calls = []
    monkeypatch.setattr(uploader, "eval_js", _make_eval_stub(eval_calls, modal_already_open=False))
    monkeypatch.setattr(uploader, "run_cdp", lambda *args, **kwargs: {})
    monkeypatch.setattr(uploader, "sleep_s", lambda *_args, **_kwargs: None)

    ok = uploader.attach_product_link(
        "e8c50275ed5d4748a046603377e8a216",
        cart_name="Logitech Lift Vertical Ergonomic Mouse ไร้สาย™",
        tab_id=123,
    )
    assert ok is True

    title_scripts = [js for js in eval_calls if "const desired =" in js]
    assert len(title_scripts) == 1
    match = re.search(r"const desired = (\"[^\"]*\");", title_scripts[0])
    assert match is not None
    assert json.loads(match.group(1)) == "เมาส์ไร้สาย Logitech Lift"


def test_attach_product_link_sanitizes_uncurated_cart_name(monkeypatch):
    eval_calls = []
    monkeypatch.setattr(uploader, "eval_js", _make_eval_stub(eval_calls, modal_already_open=True))
    monkeypatch.setattr(uploader, "run_cdp", lambda *args, **kwargs: {})
    monkeypatch.setattr(uploader, "sleep_s", lambda *_args, **_kwargs: None)

    ok = uploader.attach_product_link(
        "1731512091369702645",
        cart_name="Widget Pro Ⅱ™ Super Long Name For Testing Cart Limit",
        tab_id=123,
    )
    assert ok is True

    title_scripts = [js for js in eval_calls if "const desired =" in js]
    assert len(title_scripts) == 1
    match = re.search(r"const desired = (\"[^\"]*\");", title_scripts[0])
    assert match is not None
    desired = json.loads(match.group(1))
    assert "Ⅱ" not in desired and "™" not in desired
    assert desired.startswith("Widget Pro II")
    assert len(desired) <= 30
