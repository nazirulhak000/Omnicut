import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchViralLint } from '../lib/viralLintApi.js';

export const VIRAL_LINT_DEBOUNCE_MS = 700;

/**
 * Debounced Viral Lint of the editor's current save payload. `report` is the
 * latest result for the current project (null while unknown or when the API
 * is unreachable -- lint is advisory, a failed request never blocks render).
 * `refresh()` lints the latest payload right now; the render gate awaits it
 * so a block issue added in the last few hundred ms is still caught.
 */
export default function useViralLint({ projectName, manifest, enabled = true }) {
  const [report, setReport] = useState(null);
  const sequence = useRef(0);
  const latest = useRef({ projectName, manifest });
  latest.current = { projectName, manifest };

  const run = useCallback(async () => {
    const { projectName: name, manifest: payload } = latest.current;
    if (!name) return null;
    const ticket = ++sequence.current;
    try {
      const result = await fetchViralLint({ projectName: name, manifest: payload });
      if (ticket === sequence.current) setReport(result);
      return result;
    } catch {
      if (ticket === sequence.current) setReport(null);
      return null;
    }
  }, []);

  useEffect(() => {
    setReport(null);
    sequence.current += 1;
  }, [projectName]);

  useEffect(() => {
    if (!enabled || !projectName) return undefined;
    const timer = setTimeout(run, VIRAL_LINT_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [enabled, projectName, manifest, run]);

  useEffect(() => () => { sequence.current += 1; }, []);

  return { report, refresh: run };
}
