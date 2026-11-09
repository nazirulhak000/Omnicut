# -*- coding: utf-8 -*-
"""Image quality + duplicate gate for downloaded product images (audit S1-04).

``.agents/rules/asset_sourcing_and_deduplication.md`` forbids keeping low-res
thumbnails and byte-identical duplicates. The gate runs where an image is
actually downloaded (``product_scraper._download_image_bytes``), not when its
URL is scraped:

* an image whose short edge is under 1080 px is rejected unless the file is at
  least 100 KB (a big file with a small edge is a legitimate product photo,
  a tiny file is a thumbnail / UI icon);
* an image whose size cannot be read (Pillow cannot decode it) is judged by
  file size alone;
* :class:`ImageHashRegistry` drops byte-identical repeats by SHA-256.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from typing import Iterable, Optional, Set, Tuple

MIN_SHORT_EDGE_PX = 1080
MIN_KEEP_BYTES = 100 * 1024


@dataclass(frozen=True)
class ImageVerdict:
    ok: bool
    reason: str
    width: Optional[int]
    height: Optional[int]
    size: int
    sha256: str


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_dimensions(data: bytes) -> Optional[Tuple[int, int]]:
    """(width, height) from the image header, or None when it cannot be read."""
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as img:
            return int(img.width), int(img.height)
    except Exception:  # noqa: BLE001 - any decode problem means "unknown size"
        return None


def evaluate_image_bytes(
    data: bytes,
    *,
    min_short_edge: int = MIN_SHORT_EDGE_PX,
    min_keep_bytes: int = MIN_KEEP_BYTES,
) -> ImageVerdict:
    """Apply the 1080 px / 100 KB rule to downloaded image bytes."""
    size = len(data or b"")
    digest = sha256_of(data or b"")
    if size == 0:
        return ImageVerdict(False, "ไฟล์ภาพว่างเปล่า", None, None, 0, digest)
    dims = read_dimensions(data)
    if dims is None:
        if size >= min_keep_bytes:
            return ImageVerdict(True, "", None, None, size, digest)
        return ImageVerdict(
            False,
            f"อ่านขนาดภาพไม่ได้และไฟล์เล็กกว่า {min_keep_bytes // 1024} KB ({size / 1024:.0f} KB) — ข้าม",
            None, None, size, digest,
        )
    width, height = dims
    short_edge = min(width, height)
    if short_edge >= min_short_edge or size >= min_keep_bytes:
        return ImageVerdict(True, "", width, height, size, digest)
    return ImageVerdict(
        False,
        f"ภาพความละเอียดต่ำ {width}x{height} ({size / 1024:.0f} KB) — ด้านสั้นต่ำกว่า {min_short_edge}px "
        f"และไฟล์เล็กกว่า {min_keep_bytes // 1024} KB",
        width, height, size, digest,
    )


class ImageHashRegistry:
    """SHA-256 registry: ``register`` is True only the first time bytes are seen."""

    def __init__(self, existing: Iterable[str] = ()) -> None:
        self._seen: Set[str] = set(existing)

    def __contains__(self, digest: str) -> bool:
        return digest in self._seen

    def register(self, data: bytes) -> bool:
        digest = sha256_of(data)
        if digest in self._seen:
            return False
        self._seen.add(digest)
        return True
