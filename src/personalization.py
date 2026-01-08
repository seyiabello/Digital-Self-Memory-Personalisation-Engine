from __future__ import annotations

from typing import Dict, Any, List
from .digital_self import DigitalSelf


def derive_personalization(ds: DigitalSelf, user_query: str, short_term_items: List[dict]) -> Dict[str, Any]:
    """
    Simple, explainable rules.
    """
    rules_applied = []

    tone = ds.stable.tone
    if tone:
        rules_applied.append(f"tone={tone}")

    interests = ds.stable.interests[:5]
    if interests:
        rules_applied.append("prioritize_interests")

    dislikes = ds.stable.dislikes[:5]
    if dislikes:
        rules_applied.append("avoid_dislikes")

    return {
        "tone": tone,
        "interests": interests,
        "dislikes": dislikes,
        "rules_applied": rules_applied,
    }


def build_system_prompt(personalization: Dict[str, Any]) -> str:
    tone = personalization.get("tone", "neutral")
    interests = personalization.get("interests", [])
    dislikes = personalization.get("dislikes", [])

    lines = [
        "You are a helpful assistant.",
        "Follow the user's instructions precisely.",
        "Never invent memories. Only use the provided context blocks.",
    ]

    if tone == "concise":
        lines.append("Keep responses concise and practical. Avoid fluff.")
    elif tone == "detailed":
        lines.append("Give step-by-step explanations with clear structure.")
    else:
        lines.append("Be clear and direct.")

    if interests:
        lines.append(f"Where useful, prioritize examples related to: {', '.join(interests)}.")

    if dislikes:
        lines.append(f"Avoid focusing on: {', '.join(dislikes)}.")

    return "\n".join(lines)
