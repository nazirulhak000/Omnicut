/** Explicit empty string means "start a new One Click project". null means
 * ordinary Editor navigation may restore the last project. Keeping those two
 * states distinct prevents stale URL/localStorage/angle metadata from winning
 * over a user's deliberate Send to edit action. */
export const FRESH_EDITOR_PROJECT = '';

function projectName(value) {
  return typeof value === 'string' ? value.trim() : '';
}

export function editorProjectIntentFromPayload(payload = {}) {
  return projectName(payload.openProjectName) || FRESH_EDITOR_PROJECT;
}

export function resolveEditorProjectName({
  intent = null,
  urlProject = '',
  storedProject = '',
  angleProject = '',
} = {}) {
  if (intent !== null && intent !== undefined) return projectName(intent);
  return projectName(urlProject) || projectName(storedProject) || projectName(angleProject);
}

export function withEditorProjectAction(payload = {}, {
  openExisting = false,
  existingProjectName = '',
} = {}) {
  const next = { ...payload };
  delete next.openProjectName;
  const existing = projectName(existingProjectName);
  if (openExisting && existing) next.openProjectName = existing;
  return next;
}

export function filterActiveProjects(projects = [], statusByProject = {}) {
  return (projects || []).filter((p) => {
    const status = statusByProject[p?.project_name] || (p?.is_posted ? 'posted' : p?.status);
    return status !== 'posted';
  });
}

