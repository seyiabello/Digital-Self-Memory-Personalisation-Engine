from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

import argparse
import os
from rich.console import Console

from src.digital_self import DigitalSelf
from src.memory.session import SessionMemory
from src.memory.short_term import ShortTermMemory
from src.memory.long_term import LongTermMemory
from src.agent import handle_turn
from src.utils import safe_json_load, safe_json_dump


console = Console()


def load_or_create_digital_self(user_id: str, path: str) -> DigitalSelf:
    data = safe_json_load(path, default=None)
    if data is None:
        ds = DigitalSelf(user_id=user_id)
        safe_json_dump(path, ds.model_dump())
        return ds
    return DigitalSelf(**data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user_id", type=str, default="default_user")
    parser.add_argument("--memory_mode", type=str, default="stm_ltm", choices=["no_memory", "stm", "stm_ltm"])
    args = parser.parse_args()

    os.makedirs("data", exist_ok=True)
    ds_path = f"data/digital_self_{args.user_id}.json"
    ds = load_or_create_digital_self(args.user_id, ds_path)

    session = SessionMemory()

    # Memory modes
    if args.memory_mode == "no_memory":
        stm = ShortTermMemory(max_items=0, ttl_minutes=1)
        ltm = None
    elif args.memory_mode == "stm":
        stm = ShortTermMemory(max_items=20, ttl_minutes=240)
        ltm = None
    else:
        stm = ShortTermMemory(max_items=20, ttl_minutes=240)
        ltm = LongTermMemory(persist_dir="data/chroma", collection_name="ltm")

    console.print(f"[bold]Digital Self Engine[/bold] | user_id={args.user_id} | memory_mode={args.memory_mode}")
    console.print("Commands: :forget last | :forget all | :forget <keyword> | :show stm | :show ltm | :exit\n")

    while True:
        user_text = input("> ").strip()
        if not user_text:
            continue
        if user_text == ":exit":
            break

        out = handle_turn(user_text, ds, session, stm, ltm)

        # Persist updated digital self if present
        if "digital_self" in out:
            ds = out["digital_self"]
            safe_json_dump(ds_path, ds.model_dump())

        # Print reply
        if "reply" in out:
            console.print("\n[bold]Assistant[/bold]")
            console.print(out["reply"])

            console.print("\n[dim]Retrieval log[/dim]")
            console.print(out.get("retrieval_log", {}))

            console.print("[dim]Personalization[/dim]")
            console.print(out.get("personalization", {}))
            console.print()

    console.print("[green]Session ended. Session memory cleared by design.[/green]")


if __name__ == "__main__":
    main()
