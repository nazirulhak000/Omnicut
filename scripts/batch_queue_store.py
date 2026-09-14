"""Durable storage for multi-clip batch-render checkpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from scripts.config import BASE_DIR
from scripts.db import DocumentTable


BATCH_QUEUE_PATH = BASE_DIR / "03_Projects" / "batch_render_queue.json"


def _db_path() -> Path:
    return BATCH_QUEUE_PATH.parent / "batch_render_queue.db"


def _json_path() -> Path:
    return BATCH_QUEUE_PATH


_TABLE = DocumentTable("batch_render_queue", _db_path, _json_path)


class BatchQueueStore:
    """Small adapter so batch state can outlive the API process."""

    @classmethod
    def load(cls) -> List[Dict[str, Any]]:
        return _TABLE.load()

    @classmethod
    def mutate(cls):
        return _TABLE.mutate()
