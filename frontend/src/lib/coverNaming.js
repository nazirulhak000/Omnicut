/**
 * Resolves the stable stem used for a generated cover file.
 *
 * Project names are the canonical identity for rendered clips. Export/video
 * names remain a compatibility fallback for legacy entries that do not carry
 * project metadata yet.
 */
export function resolveCoverExportStem(videoItem) {
  if (!videoItem || typeof videoItem !== 'object') return null;

  const projectName = videoItem.project_name || videoItem.projectName;
  if (typeof projectName === 'string' && projectName.trim()) {
    return stripExtensionAndPath(projectName);
  }

  const fallback = videoItem.stem || videoItem.path || videoItem.rel_path || videoItem.name;
  if (typeof fallback !== 'string' || !fallback.trim()) return null;
  return stripExtensionAndPath(fallback);
}

function stripExtensionAndPath(value) {
  const basename = value.trim().replaceAll('\\', '/').split('/').pop() || '';
  return basename.replace(/\.[^/.]+$/, '') || null;
}
