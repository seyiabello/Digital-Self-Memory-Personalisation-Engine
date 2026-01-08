from __future__ import annotations

import json
import re
import os
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional

import numpy as np
from openai import OpenAI

# ---------- Embeddings (OpenAI) ----------
_openai_client: Optional[OpenAI] = None
_EMBED_MODEL = "text-embedding-3-small"


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client


def embed_text(text: str) -> np.ndarray:
    c = _get_openai_client()
    r = c.embeddings.create(model=_EMBED_MODEL, input=text)
    vec = r.data[0].embedding
    return np.array(vec, dtype=np.float32)


def embed_texts(texts: List[str]) -> List[np.ndarray]:
    c = _get_openai_client()
    r = c.embeddings.create(model=_EMBED_MODEL, input=texts)
    return [np.array(d.embedding, dtype=np.float32) for d in r.data]


# ---------- Time / ids / json ----------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_in_days(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def iso_in_minutes(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def parse_iso(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def is_expired(expires_at_iso: str) -> bool:
    return datetime.now(timezone.utc) >= parse_iso(expires_at_iso)


def stable_hash_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def safe_json_load(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def safe_json_dump(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


# ---------- Sensitivity detection ----------
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}\b")
_PASSWORD_HINT_RE = re.compile(r"\b(my password is|password:|passcode:)\b", re.I)
_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")


def contains_sensitive(text: str, extra_keywords: Optional[list[str]] = None) -> bool:
    if _EMAIL_RE.search(text):
        return True
    if _PASSWORD_HINT_RE.search(text):
        return True
    if _CARD_RE.search(text):
        return True
    # phone regex can false-positive, but fine for a prototype
    if _PHONE_RE.search(text):
        return True
    if extra_keywords:
        low = text.lower()
        for kw in extra_keywords:
            if kw.lower() in low:
                return True
    return False


def redact_sensitive(text: str) -> str:
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _CARD_RE.sub("[REDACTED_CARD]", text)
    text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
    return text
