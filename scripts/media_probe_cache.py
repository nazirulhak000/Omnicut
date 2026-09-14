"""Per-render cache for immutable media probe results."""

import os
from pathlib import Path
from typing import Any, Callable, Dict


class MediaProbeCache:
    """Resolve each source once and probe it at most once during one render.

    FFmpeg still receives one input per timeline clip, because each clip has
    its own seek/span. Only immutable metadata (duration, geometry, audio)
    is shared, keeping the render contract unchanged.
    """

    def __init__(self, probe: Callable[[str], Dict[str, Any]]) -> None:
        self._probe = probe
        self._entries: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _key(path: str | Path) -> str:
        return os.path.normcase(str(Path(path).resolve()))

    def get(self, path: str | Path) -> Dict[str, Any]:
        key = self._key(path)
        if key not in self._entries:
            self._entries[key] = self._probe(key)
        return self._entries[key]
