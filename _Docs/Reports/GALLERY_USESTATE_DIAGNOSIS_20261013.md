# Export Gallery useState diagnosis · 2026-10-13

ดำเนินการโดย: Codex (GPT-6)

## Observed outcome

User screenshot reports `TypeError: Cannot read properties of null (reading useState)` inside the existing error boundary. A fresh headless browser opened the running frontend at localhost:5173, selected Gallery using persisted navigation, and displayed 202 real export entries without React errors. This check was read-only; it did not modify exports or publication state.

The supplied screenshot has no call stack. The underlying error is not reproduced, so stale HMR/module state is only a hypothesis, not a confirmed root cause. No speculative runtime patch or React upgrade was made. A full page reload in the affected tab is the next recovery step; if it recurs, its console stack is needed to locate the failing module.

## Regression coverage

The old retired-menu test asserted localStorage navigation and immediately checked errors, before the lazy Gallery finished loading. It now waits for actual Gallery content, exercises empty and populated lists, grid/split modes and detail dialogs on desktop/mobile. API and media requests are mocked; no actual test media were written.

## Checks

Frontend: 1021 passed, 0 failed. Build passed in 1.27 seconds; existing chunk-size warning remains.

Jev: noul 0.81, confidence null (not code evidence); continued under the user's previously authorized tests/review workflow.

Browser regression: 12 passed in 24.41 seconds. Scoped git diff --check: exit 0.
