---

# 📄 `DESIGN.md`

```markdown
# Design Rationale

This document explains the architectural decisions behind the Digital Self Memory & Personalization Engine.

---

## Why layered memory?

Human memory is not a flat store.  
This system mirrors that by separating memory into:

- Ephemeral context (session)
- Recent working memory (STM)
- Selective, persistent semantic memory (LTM)

This avoids:
- Over-retrieval
- Context bloat
- Uncontrolled accumulation of user data

---

## Digital Self representation

The user is modeled as a structured object containing:

- **Stable traits**
  - Tone preferences
  - Interests / dislikes
  - Communication style

- **Dynamic signals**
  - Recent topics
  - Current goals
  - Last update timestamp

- **Privacy configuration**
  - Sensitive keywords
  - Retention limits
  - Do-not-store rules

This representation is serializable, inspectable, and updatable.

---

## Long-term memory design

Long-term memory is implemented using:
- Sentence embeddings
- A local vector store (Chroma)
- Metadata filtering

Each memory includes:
- Text content
- Embedding
- user_id
- Sensitivity flag
- Expiry timestamp
- Topic tags

Retrieval is:
- Semantic (not keyword-based)
- User-scoped
- Sensitivity-aware
- Logged for transparency

---

## Self-retrieval avoidance

A known failure mode in memory systems is retrieving the memory just written, leading to artificial similarity (distance ≈ 0).

This system avoids that by:
- Tracking the ID of newly stored memories
- Explicitly excluding them from retrieval on the same turn

This produces more realistic retrieval behavior.

---

## Personalization philosophy

Personalization is:
- Explicit, not inferred silently
- Rule-based, not learned opaquely
- Reversible via user commands

The system prioritizes:
- Predictability
- User agency
- Auditability

---

## Why no UI or deployment?

This project is intentionally focused on:
- Memory structure
- Context engineering
- Human-centred constraints

Adding UI, auth, or deployment would obscure the core research questions.
