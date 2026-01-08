from __future__ import annotations

from typing import List, Dict
from ..utils import now_iso


class SessionMemory:
    def __init__(self) -> None:
        self._messages: List[Dict] = []

    def add(self, role: str, content: str) -> None:
        self._messages.append({"role": role, "content": content, "ts": now_iso()})

    def get(self) -> List[Dict]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages = []
