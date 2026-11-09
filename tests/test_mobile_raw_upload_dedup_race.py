"""Two concurrent uploads of the same clip leave one raw file (audit S1-13)."""

import threading
import time

from scripts import mobile_quick_studio as mobile
from scripts import product_store
from scripts.mobile_quick_studio import MobileQuickStudioService
from scripts.product_store import ProductStore

CLIP = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42" + b"R" * 256


def test_concurrent_identical_uploads_store_one_file(tmp_path, monkeypatch):
    raw_root = tmp_path / "01_Raw"
    raw_root.mkdir()
    monkeypatch.setattr(mobile, "RAW_DIR", raw_root)
    monkeypatch.setattr(product_store, "STORE_PATH", tmp_path / "_Docs" / "products.json")
    product_store._TABLE.save([{
        "id": "prod", "name": "Test Gadget",
        "angles": [{"angle_id": "angle", "angle_name": "Review", "script_lines": ["x"]}],
    }])
    # Keep the test about the file write: store side effects are stubbed.
    monkeypatch.setattr(ProductStore, "add_video_to_product", classmethod(lambda cls, *a, **k: None))
    monkeypatch.setattr(ProductStore, "update_angle_videos", classmethod(lambda cls, *a, **k: None))

    # Widen the check-then-write window so an unlocked implementation races.
    real_find = mobile._find_duplicate_raw

    def slow_find(*args, **kwargs):
        found = real_find(*args, **kwargs)
        time.sleep(0.2)
        return found

    monkeypatch.setattr(mobile, "_find_duplicate_raw", slow_find)

    results, errors = [], []

    def upload(name):
        try:
            results.append(MobileQuickStudioService.upload_mobile_video("prod", "angle", CLIP, name))
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=upload, args=(f"take_{i}.mp4",)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    files = [p for p in (raw_root / "prod").iterdir()]
    assert len(files) == 1, files
    assert not any(p.name.endswith(".part") for p in files)
    assert {r["video_path"] for r in results} == {f"01_Raw/prod/{files[0].name}"}
