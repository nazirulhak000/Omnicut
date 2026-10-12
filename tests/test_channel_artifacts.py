import pytest

from scripts import config
from scripts.channel_artifacts import register, owners
from scripts.channel_scope import ChannelScope
from scripts.channel_store import ChannelError
from scripts.channel_workflows import require_media_owner


def test_companion_index_is_idempotent_and_foreign_owner_cannot_reassign():
    path = config.BASE_DIR / "05_Covers_Thumbnails/second/cover.jpg"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"image")
    first = register(path, "second")
    assert register(path, "second") == first
    assert owners(path) == ["second"]
    with pytest.raises(ChannelError):
        register(path, "main")
    current = ChannelScope("second", "header", False, channel={"id": "second", "status": "active"})
    assert require_media_owner(current, path) == path
    current.channel_id = "main"
    with pytest.raises(ChannelError):
        require_media_owner(current, path)


def test_companion_index_rejects_shared_raw_and_escape():
    with pytest.raises(ChannelError):
        register("01_Raw/source.mp4", "second")
    with pytest.raises(ChannelError):
        register(config.BASE_DIR.parent / "escape.jpg", "second")
