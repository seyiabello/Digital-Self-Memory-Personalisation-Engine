from __future__ import annotations

from typing import Dict, Any, Optional

from rich.console import Console

from .digital_self import (
    DigitalSelf,
    update_dynamic,
    update_stable_from_text,
    should_treat_as_sensitive,
    redact_if_needed,
)
from .memory.session import SessionMemory
from .memory.short_term import ShortTermMemory
from .memory.long_term import LongTermMemory
from .retrieval import build_context_package
from .personalization import derive_personalization, build_system_prompt
from .utils import truncate

console = Console()


def is_control_command(text: str) -> bool:
    return text.strip().startswith(":")


def handle_control_command(
    cmd: str,
    ds: DigitalSelf,
    stm: ShortTermMemory,
    ltm: Optional[LongTermMemory],
) -> bool:
    """
    Returns True if handled (and should skip normal generation).
    Commands:
      :forget last
      :forget all
      :forget <keyword>
      :show stm
      :show ltm
      :exit
    """
    parts = cmd.strip().split(maxsplit=2)
    if not parts:
        return True

    if parts[0] == ":forget":
        if len(parts) < 2:
            console.print("Usage: :forget last | :forget all | :forget <keyword>")
            return True

        target = parts[1].lower()

        if target == "last":
            recent = stm.get_recent()
            if recent:
                first_summary = recent[0].get("summary", "")
                stm.delete(lambda x: x.get("summary") == first_summary and x.get("ts") == recent[0].get("ts"))
                console.print("[green]Deleted last short-term item.[/green]")
            else:
                console.print("[yellow]No short-term items to delete.[/yellow]")
            return True

        if target == "all":
            stm.clear()
            if ltm:
                n = ltm.wipe_user(ds.user_id)
                console.print(f"[green]Cleared STM and wiped {n} long-term memories.[/green]")
            else:
                console.print("[green]Cleared STM.[/green]")
            return True

        keyword = cmd.strip().split(maxsplit=1)[1].replace("forget", "", 1).strip()
        stm_deleted = stm.delete(
            lambda x: keyword.lower() in ((x.get("text", "") + " " + x.get("summary", "")).lower())
        )
        ltm_deleted = 0
        if ltm:
            ltm_deleted = ltm.delete_by_keyword(ds.user_id, keyword)
        console.print(f"[green]Deleted STM={stm_deleted}, LTM={ltm_deleted} items matching '{keyword}'.[/green]")
        return True

    if parts[0] == ":show":
        if len(parts) < 2:
            console.print("Usage: :show stm | :show ltm")
            return True

        if parts[1].lower() == "stm":
            items = stm.get_recent()
            console.print(f"[cyan]STM items ({len(items)}):[/cyan]")
            for i, it in enumerate(items[:10], start=1):
                console.print(f"{i}. {truncate(it.get('summary',''), 140)}")
            return True

        if parts[1].lower() == "ltm":
            if not ltm:
                console.print("[yellow]LTM disabled in this memory_mode.[/yellow]")
                return True
            res = ltm.col.get(where={"user_id": ds.user_id}, include=["documents", "metadatas"])
            ids = res.get("ids", [])
            docs = res.get("documents", [])
            metas = res.get("metadatas", [])
            console.print(f"[cyan]LTM items ({len(ids)}):[/cyan]")
            for i, (mid, doc, meta) in enumerate(zip(ids[:10], docs[:10], metas[:10]), start=1):
                console.print(
                    f"{i}. {mid} | {truncate(doc or '', 140)} | sensitive={meta.get('is_sensitive') if meta else None}"
                )
            return True

        console.print("[yellow]Unknown show target.[/yellow]")
        return True

    if parts[0] == ":exit":
        return True

    console.print("[yellow]Unknown command.[/yellow]")
    return True


def should_store_long_term(user_text: str, ds: DigitalSelf) -> bool:
    t = user_text.lower()
    triggers = [
        "remember that",
        "remember this",
        "i prefer",
        "i like",
        "i hate",
        "my goal is",
        "i am working on",
        "i'm working on",
    ]
    return any(x in t for x in triggers)


def generate_response(system_prompt: str, context_text: str, user_text: str) -> str:
    """
    Minimal stub response generator.
    Swap with an LLM later.
    """
    return (
        f"{system_prompt}\n\n"
        f"I used the provided context blocks. Here’s my response:\n"
        f"- You asked: {user_text}\n"
        f"- I will answer in line with the tone rules and your recent context.\n"
        f"\nAnswer:\n"
        f"{user_text}\n"
        f"\n(Replace this generator with an LLM call when you’re ready.)"
    )


def handle_turn(
    user_text: str,
    ds: DigitalSelf,
    session: SessionMemory,
    stm: ShortTermMemory,
    ltm: Optional[LongTermMemory],
) -> Dict[str, Any]:
    if is_control_command(user_text):
        handled = handle_control_command(user_text, ds, stm, ltm)
        return {"handled_control": handled}

    session.add("user", user_text)

    sensitive = should_treat_as_sensitive(ds, user_text)

    ds = update_dynamic(ds, user_text)
    ds = update_stable_from_text(ds, user_text)

    safe_text = redact_if_needed(ds, user_text)
    stm.add(
        text=safe_text,
        summary=truncate(safe_text, 180),
        tags=ds.dynamic.recent_topics[:1],
    )

    ltm_id = None
    if ltm is not None and (not sensitive) and should_store_long_term(user_text, ds):
        from .utils import embed_text
        emb = embed_text(user_text).tolist()
        ltm_id = ltm.add(
            user_id=ds.user_id,
            text=user_text,
            embedding=emb,
            tags=[ds.dynamic.recent_topics[0]] if ds.dynamic.recent_topics else [],
            is_sensitive=False,
            retention_days=ds.privacy.retention_days.long_term,
        )

    pack = build_context_package(
        user_query=user_text,
        ds=ds,
        session=session,
        stm=stm,
        ltm=ltm,
        top_k=5,
        exclude_ltm_ids=[ltm_id] if ltm_id else None,  # avoid self-retrieval
    )

    personalization = derive_personalization(ds, user_text, pack["stm_items"])
    system_prompt = build_system_prompt(personalization)

    reply = generate_response(system_prompt, pack["context_text"], user_text)

    session.add("assistant", reply)

    return {
        "digital_self": ds,
        "reply": reply,
        "stored_long_term_id": ltm_id,
        "sensitive": sensitive,
        "retrieval_log": pack["retrieval_log"],
        "personalization": personalization,
    }

