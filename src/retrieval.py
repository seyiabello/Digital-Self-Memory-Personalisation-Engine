from __future__ import annotations

from typing import Dict, Any, List, Optional

from .digital_self import DigitalSelf
from .utils import embed_text, truncate
from .memory.short_term import ShortTermMemory
from .memory.long_term import LongTermMemory
from .memory.session import SessionMemory


MAX_DS_CHARS = 800
MAX_STM_CHARS = 800
MAX_LTM_CHARS = 1200


def _format_digital_self(ds: DigitalSelf) -> str:
    stable = ds.stable.model_dump()
    dynamic = ds.dynamic.model_dump()
    return f"STABLE: {stable}\nDYNAMIC: {dynamic}\n"


def _format_short_term(items: List[dict]) -> str:
    lines = []
    for it in items[:8]:
        summ = it.get("summary") or ""
        tags = it.get("tags") or []
        lines.append(f"- {summ} (tags={tags})")
    return "\n".join(lines)


def _format_long_term(memories: List[dict]) -> str:
    lines = []
    for m in memories:
        preview = truncate(m["text"], 220)
        lines.append(f"- {preview} (dist={m.get('distance')}, ts={m.get('ts')}, tags={m.get('tags')})")
    return "\n".join(lines)


def build_context_package(
    user_query: str,
    ds: DigitalSelf,
    session: SessionMemory,
    stm: ShortTermMemory,
    ltm: Optional[LongTermMemory],
    top_k: int = 5,
    exclude_ltm_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    q_emb = embed_text(user_query).tolist()

    recent_stm = stm.get_recent()

    ltm_hits: List[dict] = []
    if ltm is not None:
        ltm_hits = ltm.query(
            user_id=ds.user_id,
            query_embedding=q_emb,
            top_k=top_k,
            exclude_sensitive=True,
        )

    if exclude_ltm_ids:
        exclude_set = set([x for x in exclude_ltm_ids if x])
        ltm_hits = [m for m in ltm_hits if m.get("id") not in exclude_set]

    ds_block = truncate(_format_digital_self(ds), MAX_DS_CHARS)
    stm_block = truncate(_format_short_term(recent_stm), MAX_STM_CHARS)
    ltm_block = truncate(_format_long_term(ltm_hits), MAX_LTM_CHARS)

    ltm_explanations = []
    for m in ltm_hits:
        tags = m.get("tags") or []
        ltm_explanations.append(
            {
                "id": m.get("id"),
                "distance": m.get("distance"),
                "reason": f"Selected by semantic similarity to query. tags={tags}",
                "ts": m.get("ts"),
            }
        )

    retrieval_log = {
        "ltm_retrieved_count": len(ltm_hits),
        "ltm_ids": [m["id"] for m in ltm_hits],
        "ltm_top_distances": [m.get("distance") for m in ltm_hits],
        "ltm_explanations": ltm_explanations,
        "stm_count": len(recent_stm),
        "limits": {"ds": MAX_DS_CHARS, "stm": MAX_STM_CHARS, "ltm": MAX_LTM_CHARS},
    }

    context_text = (
        "=== DIGITAL SELF ===\n"
        f"{ds_block}\n\n"
        "=== SHORT-TERM MEMORY ===\n"
        f"{stm_block}\n\n"
        "=== LONG-TERM MEMORY ===\n"
        f"{ltm_block}\n"
    )

    return {
        "context_text": context_text,
        "retrieval_log": retrieval_log,
        "query_embedding": q_emb,
        "ltm_hits": ltm_hits,
        "stm_items": recent_stm,
    }

