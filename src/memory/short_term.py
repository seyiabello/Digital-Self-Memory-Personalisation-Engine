from __future__ import annotations

from typing import List, Dict, Callable, Optional
from ..utils import now_iso, iso_in_minutes, is_expired


class ShortTermMemory:
    def __init__(self, max_items: int = 20, ttl_minutes: int = 240) -> None:
        self.max_items = max_items
        self.ttl_minutes = ttl_minutes
        self._items: List[Dict] = []

    def add(self, text: str, summary: str, tags: Optional[list[str]] = None) -> Dict:
        item = {
            "text": text,
            "summary": summary,
            "tags": tags or [],
            "ts": now_iso(),
            "expires_at": iso_in_minutes(self.ttl_minutes),
        }
        self._items.insert(0, item)
        self._items = self._items[: self.max_items]
        self.decay()
        return item

    def decay(self) -> None:
        self._items = [x for x in self._items if not is_expired(x["expires_at"])]

    def get_recent(self) -> List[Dict]:
        self.decay()
        return list(self._items)

    def delete(self, predicate: Callable[[Dict], bool]) -> int:
        before = len(self._items)
        self._items = [x for x in self._items if not predicate(x)]
        return before - len(self._items)

    def clear(self) -> None:
        self._items = []
