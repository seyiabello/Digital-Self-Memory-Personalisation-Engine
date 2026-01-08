import os

os.environ["CHROMA_TELEMETRY"] = "FALSE"
os.environ["ANONYMIZED_TELEMETRY"] = "FALSE"

from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from ..utils import now_iso, iso_in_days, is_expired, stable_hash_id


class LongTermMemory:
    """
    Chroma-backed semantic memory.
    Stores:
      - documents (raw or summarized memory text)
      - embeddings
      - metadata (user_id, ts, is_sensitive, expires_at, tags)
    NOTE: Chroma metadata values must be scalar types (str/int/float/bool/None).
    """

    def __init__(self, persist_dir: str = "data/chroma", collection_name: str = "ltm") -> None:
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.col = self.client.get_or_create_collection(name=collection_name)

    def add(
        self,
        user_id: str,
        text: str,
        embedding: list[float],
        tags: Optional[list[str]] = None,
        is_sensitive: bool = False,
        retention_days: int = 30,
        memory_type: str = "long_term",
    ) -> str:
        memory_id = stable_hash_id(f"{user_id}:{text}:{now_iso()}")

        tags_str = ", ".join([t.strip() for t in (tags or []) if t and t.strip()])

        meta = {
            "user_id": user_id,
            "ts": now_iso(),
            "memory_type": memory_type,
            "is_sensitive": bool(is_sensitive),
            "expires_at": iso_in_days(retention_days),
            "tags": tags_str,  # must be scalar
        }

        self.col.add(
            ids=[memory_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[meta],
        )
        return memory_id

    def purge_expired(self, user_id: str) -> int:
        res = self.col.get(where={"user_id": user_id}, include=["metadatas"])
        ids = res.get("ids", [])
        metas = res.get("metadatas", [])

        to_delete = []
        for mid, meta in zip(ids, metas):
            if meta and "expires_at" in meta and is_expired(meta["expires_at"]):
                to_delete.append(mid)

        if to_delete:
            self.col.delete(ids=to_delete)
        return len(to_delete)

    def delete_by_id(self, memory_id: str) -> None:
        self.col.delete(ids=[memory_id])

    def delete_by_keyword(self, user_id: str, keyword: str) -> int:
        res = self.col.get(where={"user_id": user_id}, include=["documents"])
        ids = res.get("ids", [])
        docs = res.get("documents", [])

        to_delete = []
        for mid, doc in zip(ids, docs):
            if doc and keyword.lower() in doc.lower():
                to_delete.append(mid)

        if to_delete:
            self.col.delete(ids=to_delete)
        return len(to_delete)

    def wipe_user(self, user_id: str) -> int:
        res = self.col.get(where={"user_id": user_id}, include=[])
        ids = res.get("ids", [])
        if ids:
            self.col.delete(ids=ids)
        return len(ids)

    def query(
        self,
        user_id: str,
        query_embedding: list[float],
        top_k: int = 5,
        exclude_sensitive: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Returns list of dicts with:
          id, text, distance, ts, tags (list), is_sensitive, expires_at
        """
        self.purge_expired(user_id)

        # Chroma requires exactly one top-level operator in `where`.
        if exclude_sensitive:
            where: Dict[str, Any] = {"$and": [{"user_id": user_id}, {"is_sensitive": False}]}
        else:
            where = {"user_id": user_id}

        res = self.col.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        out: List[Dict[str, Any]] = []
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        for mid, doc, meta, dist in zip(ids, docs, metas, dists):
            if not meta:
                continue
            if "expires_at" in meta and is_expired(meta["expires_at"]):
                continue

            raw_tags = meta.get("tags", "") or ""
            tags_list = [t.strip() for t in raw_tags.split(",") if t.strip()]

            out.append(
                {
                    "id": mid,
                    "text": doc,
                    "distance": float(dist) if dist is not None else None,
                    "ts": meta.get("ts"),
                    "tags": tags_list,
                    "is_sensitive": bool(meta.get("is_sensitive", False)),
                    "expires_at": meta.get("expires_at"),
                }
            )

        return out


