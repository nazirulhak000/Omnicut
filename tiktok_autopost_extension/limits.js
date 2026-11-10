// Every number the posting stack agrees on, in one place (worker, side panel, orchestrator, guard, conductor).
// tests/test_content_guard.py and the node tests check that the Python twin and the consumers still match these.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.OmniLimits = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  return Object.freeze({
    SCHEDULE_CAP: 30,                    // TikTok: scheduled posts per account
    DRAFT_CAP: 30,                       // TikTok: drafts per account
    MIN_LEAD_MS: 15 * 60 * 1000,         // a scheduled slot must be at least this far ahead
    ACCOUNT_REREAD_MS: 15 * 60 * 1000,   // how long a verified TikTok account handle is trusted for one job chain
    MAX_TEXT_CHARS: 4000,                // caption + hashtags
    MAX_HASHTAGS: 30,
    CLIP_BUDGET_MIN: 25,                 // conductor: time budget per clip
    COOLDOWN_SECONDS: 22,                // panel: base pause between clips (jittered)
  });
});
