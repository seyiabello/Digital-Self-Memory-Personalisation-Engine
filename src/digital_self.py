from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from .utils import now_iso, contains_sensitive, redact_sensitive


class RetentionDays(BaseModel):
    short_term: int = 1
    long_term: int = 30


class PrivacyConfig(BaseModel):
    sensitive_keywords: list[str] = Field(default_factory=lambda: ["password", "bank", "card", "ni number"])
    do_not_store: list[str] = Field(default_factory=lambda: ["password", "bank", "card", "medical"])
    retention_days: RetentionDays = Field(default_factory=RetentionDays)


class StableTraits(BaseModel):
    tone: str = "neutral"
    interests: list[str] = Field(default_factory=list)
    dislikes: list[str] = Field(default_factory=list)
    timezone: str = "Europe/London"
    communication_style: str = "clear"


class DynamicSignals(BaseModel):
    recent_topics: list[str] = Field(default_factory=list)
    current_goals: list[str] = Field(default_factory=list)
    last_updated: str = Field(default_factory=now_iso)


class Profile(BaseModel):
    embedding: Optional[list[float]] = None
    embedding_model: str = "text-embedding-3-small"  # matches OpenAI embeddings


class DigitalSelf(BaseModel):
    user_id: str
    stable: StableTraits = Field(default_factory=StableTraits)
    dynamic: DynamicSignals = Field(default_factory=DynamicSignals)
    profile: Profile = Field(default_factory=Profile)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)


def should_treat_as_sensitive(ds: DigitalSelf, text: str) -> bool:
    return contains_sensitive(text, ds.privacy.sensitive_keywords)


def redact_if_needed(ds: DigitalSelf, text: str) -> str:
    return redact_sensitive(text) if should_treat_as_sensitive(ds, text) else text


def _push_topic(ds: DigitalSelf, label: str) -> None:
    """
    Add a topic label to the front of recent_topics:
    - normalize
    - dedupe
    - cap length
    """
    label = (label or "").strip().lower()
    if not label:
        return

    # remove existing occurrence to avoid duplicates
    ds.dynamic.recent_topics = [t for t in ds.dynamic.recent_topics if t != label]
    ds.dynamic.recent_topics = ([label] + ds.dynamic.recent_topics)[:10]


def update_dynamic(ds: DigitalSelf, user_text: str, topic: Optional[str] = None) -> DigitalSelf:
    ds.dynamic.last_updated = now_iso()

    if topic:
        _push_topic(ds, topic)
        return ds

    t = user_text.lower()

    # Minimal, explainable topic labels (extend later if you want)
    if any(k in t for k in ["memory", "remember", "recall", "store this"]):
        label = "memory"
    elif any(k in t for k in ["privacy", "password", "sensitive", "data retention", "delete this"]):
        label = "privacy"
    elif any(k in t for k in ["devops", "kubernetes", "terraform", "docker", "ci/cd"]):
        label = "devops"
    elif "python" in t:
        label = "python"
    else:
        label = "general"

    _push_topic(ds, label)
    return ds


def update_stable_from_text(ds: DigitalSelf, user_text: str) -> DigitalSelf:
    """
    Minimal heuristic extraction:
    - tone preference
    - explicit interests/dislikes
    Keep it simple and explainable.
    """
    t = user_text.lower()

    # Tone signals (expanded + more robust)
    concise_signals = [
        "be concise",
        "keep it short",
        "concise answers",
        "prefer concise",
        "i prefer concise",
        "i prefer concise answers",
        "no fluff",
        "avoid fluff",
    ]
    detailed_signals = [
        "be detailed",
        "step by step",
        "walk me through",
        "in detail",
    ]

    if any(s in t for s in concise_signals):
        ds.stable.tone = "concise"
    elif any(s in t for s in detailed_signals):
        ds.stable.tone = "detailed"

    # Interests (store original snippet, compare lowercase)
    if "i like " in t:
        raw = user_text.split("i like ", 1)[1]
        interest = raw.split(".")[0].strip()
        if interest:
            existing = [x.lower() for x in ds.stable.interests]
            if interest.lower() not in existing:
                ds.stable.interests.append(interest)

    # Dislikes
    if "i hate " in t or "i don't like " in t:
        key = "i hate " if "i hate " in t else "i don't like "
        raw = user_text.lower().split(key, 1)[1]
        dislike = raw.split(".")[0].strip()
        if dislike:
            existing = [x.lower() for x in ds.stable.dislikes]
            if dislike.lower() not in existing:
                ds.stable.dislikes.append(dislike)

    return ds
