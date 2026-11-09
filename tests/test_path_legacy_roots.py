"""Audit X-02 / D8: absolute paths under a former project root are rebased
onto BASE_DIR at read time (stored data is never mutated)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import path_utils


LEGACY = r"D:\Winona\Programmer\Capcut"


@pytest.fixture
def base(tmp_path: Path) -> Path:
    root = tmp_path / "Omnicut"
    (root / "01_Raw" / "20260101_demo").mkdir(parents=True)
    (root / "01_Raw" / "20260101_demo" / "clip.mp4").write_bytes(b"x")
    return root


def test_legacy_root_rebased_when_file_exists(base):
    stored = LEGACY + r"\01_Raw\20260101_demo\clip.mp4"
    assert path_utils.to_absolute(stored, base_dir=base) == base / "01_Raw/20260101_demo/clip.mp4"


def test_legacy_root_match_is_case_insensitive_and_slash_agnostic(base):
    stored = "d:/winona/PROGRAMMER/capcut/01_Raw/20260101_demo/clip.mp4"
    assert path_utils.to_absolute(stored, base_dir=base) == base / "01_Raw/20260101_demo/clip.mp4"


def test_legacy_root_not_rebased_when_rebased_file_missing(base):
    stored = LEGACY + r"\01_Raw\20260101_demo\missing.mp4"
    assert path_utils.to_absolute(stored, base_dir=base) == Path(stored)


def test_similar_prefix_is_not_a_legacy_root(base):
    # "Capcut2" must not match the "Capcut" legacy root.
    (base / "x.mp4").write_bytes(b"x")
    stored = r"D:\Winona\Programmer\Capcut2\x.mp4"
    assert path_utils.to_absolute(stored, base_dir=base) == Path(stored)


def test_extra_legacy_root_from_env(base, tmp_path, monkeypatch):
    other = tmp_path / "Old Project Root"
    monkeypatch.setenv(path_utils.LEGACY_ROOTS_ENV, str(other))
    stored = str(other / "01_Raw" / "20260101_demo" / "clip.mp4")
    assert path_utils.to_absolute(stored, base_dir=base) == base / "01_Raw/20260101_demo/clip.mp4"


def test_paths_inside_base_and_relative_paths_unchanged(base):
    inside = base / "01_Raw" / "20260101_demo" / "clip.mp4"
    assert path_utils.to_absolute(str(inside), base_dir=base) == inside
    assert path_utils.to_absolute("01_Raw/20260101_demo/clip.mp4", base_dir=base) == inside


def test_unknown_foreign_root_passes_through(base):
    stored = r"E:\Somewhere\Else\01_Raw\20260101_demo\clip.mp4"
    assert path_utils.to_absolute(stored, base_dir=base) == Path(stored)
