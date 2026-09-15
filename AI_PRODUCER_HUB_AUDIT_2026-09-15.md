# AI Producer Hub Read-only Audit ? 2026-09-15

Executed by: Codex (GPT-6)
Scope: read-only inspection of `scripts/api_producer.py`, Producer Hub/Quick Ref UI, existing tests, and project architecture notes. No production data or credentials were changed.

## Findings

1. **SSRF and local file exposure (P1):** `scripts/api_producer.py:329-381` accepts external URLs without redirect/private-IP validation and accepts absolute local paths. A request can therefore reach private network targets or send local files to Gemini.
2. **Concurrent notes writes (P1/P2):** `scripts/api_producer.py:84-90` uses one temporary file without a lock or revision guard. Concurrent add/delete operations can lose updates.
3. **Offline merge loss (P1/P2):** `frontend/src/components/producer/QuickRefPage.jsx:113-140` and `ProducerHub.jsx:128-168` replace local notes with server responses without merging pending offline edits.
4. **Optimistic rollback (P2):** Quick Ref pin/edit paths at `QuickRefPage.jsx:576-630` do not restore local state when the API call fails.
5. **Mobile image MIME edge case (P2):** `processImageFiles()` rejects files with an empty MIME even when the extension identifies an image, affecting some iOS paste/HEIC flows.
6. **Clipboard error handling (P2):** copy feedback is shown before `navigator.clipboard.writeText()` settles and rejection is not surfaced.
7. **Architecture documentation drift (P2):** `ARCHITECTURE.md` still describes eight modules and Edge-TTS while Producer Hub/Quick Ref and Gemini defaults are present.

## Evidence and gaps

- Backend Producer tests: 9 passed.
- Frontend test suite: 246 passed.
- Missing regression coverage: SSRF/local path, concurrent notes, offline merge, optimistic rollback, empty MIME image input, and clipboard rejection.

## Recommended next work

Create separate bounded hardening rounds: (1) media URL/local-path containment and redirect validation; (2) notes revision/atomic-write contract; (3) offline merge and optimistic rollback; (4) tolerant image MIME detection and clipboard rejection feedback; (5) architecture documentation refresh.
