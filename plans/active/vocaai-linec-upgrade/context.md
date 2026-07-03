# Context: Line C VocaAI Upgrade

## Project Snapshot

- Repo: `/home/ros/ClaudeCode/Language_learner`
- Branch at start: `feature/chinese-word-focus`
- User role: Line C owner, Linux beginner
- Goal: make the current Line C prototype feel closer to VocaAI's learning loop while keeping the current skeleton intact.

## Verified Codebase Facts

### Current source tree

- `src/line_c/domain/`
  - `word.py`
  - `vocabulary_state.py`
  - `learning_record.py`
- `src/line_c/engine/`
  - `conversation_manager.py`
  - `prompt_builder.py`
  - `state_machine.py`
  - `sm2_srs.py`
  - `srs_scheduler.py`
  - `vocabulary_repository.py`
- `src/line_c/llm/`
  - `base.py`
  - `mock_llm.py`
  - `cloud_llm.py`
- `src/line_c/tts/`
  - `base.py`
  - `mock_tts.py`
- `src/line_c/ui/`
  - `main_window.py`
  - `word_summary.py`
  - `chat_bubble.py`
  - `character_widget.py`
  - `status_indicator.py`
- `tests/`
  - `test_conversation_manager.py`
  - `test_prompt_builder.py`
  - `test_sm2_srs.py`
  - `test_srs_scheduler.py`
  - `test_state_machine.py`
  - `test_tts.py`
  - `test_vocabulary_repository.py`

### Key current behavior

- `ConversationManager` still owns user-message flow, LLM call, and word events.
- `_scan_llm_response()` currently scans the assistant reply broadly for CET words and appends them to `_recent_words`.
- `_record_word_used()` currently moves words toward `ATTEMPTED` / `LEARNING` based on usage count.
- `WordSummary` keeps three parallel lists (`_target`, `_used`, `_learning`), which can show the same word more than once.
- `VocabularyRepository` stores dictionary data and the `state` field in `words`, but no dedicated mastery/event tables yet.
- `SRSScheduler` already works from 0-5 quality values.

## Important Design Decisions

1. **Keep the five-stage state machine.**
   - Reason: it is already in the codebase and fits the UI. Add `mastery_score` for finer progress instead of replacing it.

2. **Add learning data tables instead of overloading `words`.**
   - Reason: dictionary data and user-learning data should stay separate.

3. **Start with rule-based evaluation.**
   - Reason: it is testable and does not depend on cloud model stability.

4. **Use CloudLLM for final acceptance.**
   - Reason: user explicitly asked that acceptance testing should use the cloud backend.

5. **Keep UI changes small at first.**
   - Reason: the goal is to unlock the learning loop, not redesign the whole interface yet.

## Research Notes

### 1) SM-2 algorithm reference
- Source: [SuperMemo SM-2](https://www.super-memory.com/english/ol/sm2.htm)
- Useful points:
  - quality is graded 0-5
  - quality < 3 restarts the item’s repetition schedule
  - successful repetitions begin with 1 day, then 6 days, then multiply by EF
  - EF should not drop below 1.3

### 2) VocaAI patent reference
- Source: [US 2024/0321131 A1](https://patentimages.storage.googleapis.com/5f/9c/76/c96c8ce6acf8ba/US20240321131A1.pdf)
- Fetch result caveat:
  - the PDF text was not machine-readable in the provided excerpt, so I could not reliably quote detailed sections from it here.
  - The plan still follows the user’s uploaded deep research report, which already extracted the relevant learning-loop ideas.

### 3) Adaptive learning reference
- Source: [Adaptemy latest innovations](https://www.adaptemy.com/latest-innovations-in-language-learning/)
- Useful points:
  - adaptive practice timing based on forgetting prediction
  - richer learner signals than right/wrong
  - individualized forgetting profiles

### 4) Visualization reference
- Source: [arXiv 2204.08033](https://arxiv.org/pdf/2204.08033v1)
- Useful points:
  - dashboard / correction / trend views
  - sentence-level review
  - feedback grouped by grammar, vocabulary, fluency

## Files Most Likely to Change

### New files
- `src/line_c/domain/learning_event.py`
- `src/line_c/engine/learning_evaluator.py`
- `src/line_c/engine/mastery_scorer.py`
- `src/line_c/engine/target_word_tracker.py`
- `tests/test_learning_event.py`
- `tests/test_learning_evaluator.py`
- `tests/test_mastery_scorer.py`

### Existing files
- `src/line_c/engine/conversation_manager.py`
- `src/line_c/engine/prompt_builder.py`
- `src/line_c/engine/vocabulary_repository.py`
- `src/line_c/ui/word_summary.py`
- `tests/test_conversation_manager.py`
- `tests/test_vocabulary_repository.py`

### Likely unchanged for this slice
- `src/main.py`
- `src/line_c/llm/*`
- `src/line_c/tts/*`
- `src/line_c/ui/main_window.py`

## Resume Notes

- The plan is approved by the user.
- The next implementation step should start with the smallest core data model: `learning_event.py` and `mastery_scorer.py`.
- After that, wire `learning_evaluator.py`, then extend the repository, then update `ConversationManager`, then fix `WordSummary`.
- Acceptance should include at least one CloudLLM-based run, not only pytest.
