import os

from scripts.media_probe_cache import MediaProbeCache


def test_media_probe_cache_probes_a_resolved_source_once(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    calls = []

    def probe(path):
        calls.append(path)
        return {"duration": 12.0}

    cache = MediaProbeCache(probe)

    assert cache.get(source)["duration"] == 12.0
    assert cache.get(str(source)) == {"duration": 12.0}
    assert calls == [os.path.normcase(str(source.resolve()))]


def test_media_probe_cache_keeps_distinct_sources_separate(tmp_path):
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    calls = []

    cache = MediaProbeCache(lambda path: calls.append(path) or {"path": path})

    assert cache.get(first)["path"] == os.path.normcase(str(first.resolve()))
    assert cache.get(second)["path"] == os.path.normcase(str(second.resolve()))
    assert len(calls) == 2
