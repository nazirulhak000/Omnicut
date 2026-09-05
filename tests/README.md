# Test suites

Run the complete automated safety net from the repository root:

```powershell
python -m pytest tests/ -q -p no:cacheprovider --tb=short
```

The suites have separate purposes:

- `test_refactor_baseline_contracts.py` protects API routes, old manifests, Editor save payloads, and save/reload behavior.
- `test_preview_render_parity.py` checks source-level contracts between the Canvas preview and renderer.
- `test_preview_render_behavior.py` runs black-box FFmpeg output checks using files created only under pytest's temporary directory.
- `test_phase1_smoke.py` covers manifest, pipeline, reroll, media, and renderer logic without touching live project data.

Files listed in `conftest.py` are manual diagnostics retained for historical use. They render media or call external services at import time, so pytest must not collect them as automated tests.

To roll back a completed refactor commit while preserving later history, record its hash in `REFACTOR_PLAN.md` and run:

```powershell
git revert <commit-hash>
```

When the working tree already contains unrelated work, do not use `git reset`, `git checkout`, or `git clean` as a rollback method.
