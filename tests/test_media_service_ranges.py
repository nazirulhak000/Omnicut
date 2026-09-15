"""Range responses are deterministic and operate only on temporary media."""

from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from scripts.media_service import stream_media_file


def request(range_header: str | None = None) -> Request:
    headers = [(b"range", range_header.encode())] if range_header else []
    return Request({"type": "http", "method": "GET", "path": "/media", "headers": headers})


def test_suffix_and_clamped_ranges_return_the_requested_bytes(tmp_path):
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"0123456789")
    suffix = stream_media_file(media, request("bytes=-4"))
    clamped = stream_media_file(media, request("bytes=7-99"))
    assert suffix.status_code == 206
    assert suffix.headers["content-range"] == "bytes 6-9/10"
    assert suffix.body == b"6789"
    assert clamped.headers["content-range"] == "bytes 7-9/10"
    assert clamped.body == b"789"


@pytest.mark.parametrize("value", ["bytes=10-10", "bytes=7-3", "bytes=abc-def", "bytes=0-1,3-4"])
def test_invalid_or_unsatisfiable_range_is_416(tmp_path, value):
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"0123456789")
    with pytest.raises(HTTPException) as caught:
        stream_media_file(media, request(value))
    assert caught.value.status_code == 416
    assert caught.value.headers == {"Content-Range": "bytes */10"}


def test_range_on_empty_media_is_416(tmp_path):
    media = tmp_path / "empty.mp4"
    media.write_bytes(b"")
    with pytest.raises(HTTPException) as caught:
        stream_media_file(media, request("bytes=0-0"))
    assert caught.value.status_code == 416
    assert caught.value.headers == {"Content-Range": "bytes */0"}
