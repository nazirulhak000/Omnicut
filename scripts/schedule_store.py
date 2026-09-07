"""Durable queue records for the multi-day TikTok publishing agenda."""

from __future__ import annotations

import datetime as dt
import uuid
from pathlib import Path
from typing import Any, Dict, List

from scripts.config import BASE_DIR
from scripts.db import DocumentTable

SCHEDULE_QUEUE_PATH = BASE_DIR / "_Docs" / "schedule_queue.json"
SCHEDULE_TEMPLATE_PATH = BASE_DIR / "_Docs" / "schedule_templates.json"


def _db_path() -> Path:
    return SCHEDULE_QUEUE_PATH.parent / "store.db"


def _json_path() -> Path:
    return SCHEDULE_QUEUE_PATH


def _template_db_path() -> Path:
    return SCHEDULE_TEMPLATE_PATH.parent / "store.db"


def _template_json_path() -> Path:
    return SCHEDULE_TEMPLATE_PATH


_TABLE = DocumentTable("schedule_queue", _db_path, _json_path)
_TEMPLATE_TABLE = DocumentTable("schedule_templates", _template_db_path, _template_json_path)


class ScheduleQueueStore:
    @classmethod
    def _load(cls) -> List[Dict[str, Any]]:
        return _TABLE.load()

    @classmethod
    def _save(cls, records: List[Dict[str, Any]]) -> None:
        _TABLE.save(records)

    @classmethod
    def _mutate(cls):
        return _TABLE.mutate()


class ScheduleTemplateStore:
    """Durable weekly schedule templates, kept separate from queue rows."""

    @classmethod
    def _load(cls) -> List[Dict[str, Any]]:
        return _TEMPLATE_TABLE.load()

    @classmethod
    def _save(cls, records: List[Dict[str, Any]]) -> None:
        _TEMPLATE_TABLE.save(records)

    @classmethod
    def _mutate(cls):
        return _TEMPLATE_TABLE.mutate()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex
