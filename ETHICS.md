# Ethical Considerations

This project treats memory as a sensitive capability, not a neutral feature.

---

## Data minimization

The system:
- Does not store everything by default
- Stores long-term memory only when heuristics indicate value
- Keeps summaries instead of raw transcripts where possible

---

## Sensitive data handling

The system detects sensitive content using:
- Pattern matching (e.g. passwords, financial data)
- Configurable sensitive keyword lists

When sensitive data is detected:
- It is redacted for short-term use
- It is **never stored** in long-term memory

This behavior is verifiable via memory inspection commands.

---

## User control & forgetting

Users can:
- Delete the most recent memory
- Delete all memories
- Delete memories by keyword
- End sessions (automatic session memory purge)

Forgetting is treated as a **first-class feature**, not an afterthought.

---

## Transparency & auditability

The system exposes:
- What memories were retrieved
- Why they were retrieved
- Their similarity scores
- Their metadata

This avoids hidden influence on responses.

---

## Non-goals

This system explicitly avoids:
- Behavioral profiling
- Implicit psychological inference
- Cross-user memory sharing
- Training on user data

---

## Guiding principle

Personalization should increase usefulness **without reducing autonomy**.

Memory relevance and the ability to forget are more important than remembering everything.
