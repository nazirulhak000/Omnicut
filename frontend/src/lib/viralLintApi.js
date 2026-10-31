import api from '../api.js';
import { normalizeViralLintReport } from './renderPreflight.js';

/**
 * POST /api/viral-lint (scripts/api_viral_lint.py). `manifest` is the editor's
 * current save payload; the server lays it over the stored project so
 * style_preset, script and target duration still come from the project.
 * Resolves to the normalized report, or null when the response is malformed.
 */
export async function fetchViralLint({ projectName, manifest } = {}) {
  const response = await api.post('/viral-lint', {
    project_name: projectName || null,
    manifest: manifest ?? null,
  }, { timeout: 15000 });
  return normalizeViralLintReport(response.data);
}
