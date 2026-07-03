# Line C VocaAI Upgrade — Archived Plan Snapshot

This plan is now a compact archive pointer. The active implementation details live in `DEVELOPMENT_LOG.md`.

## Completed

- Learning event model
- Mastery scoring
- Rule-based learning evaluation
- CloudLLM JSON evaluation with fallback
- Active target word tracking
- Correction feedback in chat
- Free-chat correction spam reduction
- Learning summary fields
- WordSummary deduplication

## Remaining

- More precise Chinese-focus to English-target mapping
- Learning-report UI
- Three learning modes
- SRS persistence

## Decision snapshot

- Keep the five-stage state machine.
- Keep SQLite.
- Keep SM-2.
- Prefer rule evaluation first, CloudLLM as enhancement.
- Keep UI changes minimal until learning logic is stable.
