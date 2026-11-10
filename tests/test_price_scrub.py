"""No price wording in captions: enforced in code at generation, at the storage door and by the maintenance tool."""
import pytest

from scripts import product_store as ps
from scripts.content_guard import content_reason
from scripts.product_scraper import has_price_text, scrub_angle_price_text


def test_detection_catches_price_discount_and_promo_but_not_spec_words():
    for bad in ("ลดราคาแรงมาก", "ราคาพิเศษในตะกร้า", "หัวชาร์จ 50 บาท", "รับโปรโมชั่นเด็ด", "คูปองลดเพิ่ม", "ลดโหดสุดๆ", "ลด 30%"):
        assert has_price_text(bad), bad
    for ok in ("ลดเสียงรบกวนได้ดี", "พัดลมเงียบ ดูในตะกร้า", "ชิปโปรเซสเซอร์แรง", "ใช้งานได้ 12 ชั่วโมง"):
        assert not has_price_text(ok), ok
    # a percentage is fine ON the video (hook) but blocks a post (caption): the two checks differ on purpose
    assert has_price_text("แบตเหลือ 3%!", caption=True) and not has_price_text("แบตเหลือ 3%!", caption=False)


def test_a_price_caption_is_replaced_whole_and_the_result_passes_the_posting_guard():
    angle = {
        "tiktok_caption": "ลดราคาแรงมาก! Logitech Wave Keys ราคาดีที่สุดเฉพาะช่วงนี้",
        "hook_title": "🔥 ช้าหมดอดราคาพิเศษ!",
        "price_deal": "ราคาพิเศษสุดเฉพาะวันนี้",
        "tiktok_hashtags": "#โปรโมชั่น #ลดราคา #คีย์บอร์ดไร้สาย #ของดีบอกต่อ",
    }
    changed = scrub_angle_price_text(angle, "Logitech Wave Keys คีย์บอร์ดไร้สายเพื่อสุขภาพข้อมือ")
    assert set(changed) == {"tiktok_caption", "hook_title", "price_deal", "tiktok_hashtags"}
    assert angle["tiktok_hashtags"] == "#คีย์บอร์ดไร้สาย #ของดีบอกต่อ"                 # only the offending tags go
    assert "Logitech Wave Keys" in angle["tiktok_caption"] and "ราคา" not in angle["tiktok_caption"]
    assert content_reason(angle["tiktok_caption"], angle["tiktok_hashtags"]) == ""
    assert not any(has_price_text(v) for v in angle.values())


def test_a_clean_angle_is_left_alone_and_hashtags_never_end_up_empty():
    angle = {"tiktok_caption": "เช็กก่อนซื้อ ดูในตะกร้า 👇", "hook_title": "POV: แบตเหลือ 3%!", "tiktok_hashtags": "#ลดราคา #โปรโมชั่น"}
    changed = scrub_angle_price_text(angle, "สินค้า")
    assert set(changed) == {"tiktok_hashtags"} and angle["tiktok_hashtags"] == "#ของดีบอกต่อ #tiktokป้ายยา"
    assert angle["hook_title"] == "POV: แบตเหลือ 3%!"


def test_the_neutral_name_is_cut_at_a_word_never_mid_word():
    angle = {"tiktok_caption": "ราคาถูกมาก"}
    scrub_angle_price_text(angle, "พัดลมระบายความร้อนโทรศัพท์ BlueWow X300 Pro Max")
    assert "BlueWow" not in angle["tiktok_caption"] or "BlueWow " in angle["tiktok_caption"]
    assert "Blu " not in angle["tiktok_caption"]


def test_price_script_lines_are_dropped_only_while_enough_lines_remain():
    angle = {"script_lines": ["เปิดเรื่อง", "จุดเด่นหนึ่ง", "จุดเด่นสอง", "ตอนนี้ลดราคา 50%", "ปิดท้าย"]}
    assert scrub_angle_price_text(angle, "x", fields=[], script_lines=True)["script_lines"] == (5, 4)
    assert "ตอนนี้ลดราคา 50%" not in angle["script_lines"]
    short = {"script_lines": ["ราคา 99 บาท", "สอง", "สาม"]}
    assert scrub_angle_price_text(short, "x", fields=[], script_lines=True) == {} and len(short["script_lines"]) == 3


def _product_with(angles):
    product = ps.ProductStore.add(name="สายชาร์จทดสอบ", url="https://x.test/p1", angles=angles)
    return product["id"]


def test_replace_angle_content_scrubs_a_rerolled_script_at_the_storage_door():
    pid = _product_with([{"angle_id": "pain_point", "status": "scripted", "tiktok_caption": "เดิม ดูในตะกร้า"}])
    product = ps.ProductStore.replace_angle_content(pid, "pain_point", {"tiktok_caption": "ลดราคา 50% วันนี้", "hook_title": "ชาร์จไว"})
    angle = product["angles"][0]
    assert angle["hook_title"] == "ชาร์จไว" and "ลดราคา" not in angle["tiktok_caption"]
    assert content_reason(angle["tiktok_caption"], "") == ""


def test_the_maintenance_run_previews_then_applies_and_never_touches_posted_clips():
    pid = _product_with([
        {"angle_id": "a_posted", "status": "posted", "tiktok_caption": "ราคาพิเศษ", "hook_title": "ลดราคา"},
        {"angle_id": "a_script", "status": "scripted", "tiktok_caption": "ลดราคา", "hook_title": "โปรโมชั่นแรง", "price_deal": "ราคาโปร"},
        {"angle_id": "a_render", "status": "rendered", "tiktok_caption": "ลดราคา", "hook_title": "ลดราคาโหด", "tiktok_hashtags": "#ลดราคา #ดี"},
    ])
    preview = ps.ProductStore.scrub_price_text()
    assert preview["applied"] is False and preview["posted_untouched"] == 1
    assert {(c["angle_id"], c["field"]) for c in preview["changes"]} == {
        ("a_script", "tiktok_caption"), ("a_script", "hook_title"), ("a_script", "price_deal"),
        ("a_render", "tiktok_caption"), ("a_render", "tiktok_hashtags")}
    assert [k["angle_id"] for k in preview["kept_hook"]] == ["a_render"]               # inside the rendered video: reported, not rewritten
    before = {a["angle_id"]: a for a in ps.ProductStore.snapshot(all_channels=True)[0]["angles"]}
    assert before["a_script"]["tiktok_caption"] == "ลดราคา"                           # a preview wrote nothing

    ps.ProductStore.scrub_price_text(apply=True)
    after = {a["angle_id"]: a for a in ps.ProductStore.snapshot(all_channels=True)[0]["angles"]}
    assert after["a_posted"]["tiktok_caption"] == "ราคาพิเศษ" and after["a_posted"]["hook_title"] == "ลดราคา"
    assert after["a_render"]["hook_title"] == "ลดราคาโหด"
    assert all(not has_price_text(after[k][f]) for k, f in (("a_script", "tiktok_caption"), ("a_script", "hook_title"), ("a_render", "tiktok_caption")))
    assert after["a_render"]["tiktok_hashtags"] == "#ดี"
    assert ps.ProductStore.scrub_price_text()["changes"] == []                          # idempotent
