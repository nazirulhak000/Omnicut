/**
 * Accurately matches an export item in the Export Gallery against a navigation
 * target descriptor or string.
 *
 * Supports:
 * - Rich descriptor: { exportId, videoPath, projectName, productId, angleId, targetStr }
 * - String identifier: project name, filename, path, or partial stem
 */

function clean(str) {
  return String(str || '').trim().toLowerCase();
}

function normalizeBasename(pathStr) {
  const s = clean(pathStr);
  const name = s.split(/[/\\]/).pop() || s;
  return name.replace(/\.[a-z0-9]+$/i, '');
}

export function matchExportVideo(item, target) {
  if (!item || !target) return false;

  // 1. If target is an object descriptor
  if (typeof target === 'object') {
    // Exact export_id match
    if (target.exportId && item.export_id && clean(item.export_id) === clean(target.exportId)) {
      return true;
    }

    // Exact video path / relative path match
    if (target.videoPath) {
      const targetPath = clean(target.videoPath);
      const itemPath = clean(item.path);
      const itemRel = clean(item.rel_path);
      const itemName = clean(item.name);
      if (itemPath === targetPath || itemRel === targetPath || itemName === targetPath) return true;
      if (itemPath.endsWith(targetPath) || targetPath.endsWith(itemRel)) return true;

      const targetBase = normalizeBasename(targetPath);
      const itemBase = normalizeBasename(itemName);
      if (targetBase && itemBase && (targetBase === itemBase || targetBase.includes(itemBase) || itemBase.includes(targetBase))) {
        return true;
      }
    }

    // Project name match
    if (target.projectName) {
      const targetProj = clean(target.projectName);
      const itemProj = clean(item.project_name);
      const itemName = clean(item.name);
      if (itemProj && (itemProj === targetProj || itemProj.includes(targetProj) || targetProj.includes(itemProj))) {
        return true;
      }
      const projBase = normalizeBasename(targetProj);
      const itemBase = normalizeBasename(itemName);
      if (projBase && itemBase && (projBase === itemBase || itemBase.includes(projBase) || projBase.includes(itemBase))) {
        return true;
      }
    }

    // Product ID + Angle ID match (prioritizing is_latest)
    if (target.productId && target.angleId) {
      if (clean(item.product_id) === clean(target.productId) && clean(item.angle_id) === clean(target.angleId)) {
        if (item.is_latest) return true;
      }
    }

    // Sub-target string fallback
    if (target.targetStr) {
      return matchExportVideo(item, target.targetStr);
    }

    return false;
  }

  // 2. If target is a string
  const targetStr = clean(target);
  if (!targetStr) return false;

  const exportId = clean(item.export_id);
  const name = clean(item.name);
  const path = clean(item.path);
  const relPath = clean(item.rel_path);
  const projName = clean(item.project_name);
  const hookTitle = clean(item.hook_title);

  if (exportId && exportId === targetStr) return true;
  if (name === targetStr || projName === targetStr) return true;
  if (path === targetStr || relPath === targetStr) return true;

  const targetBase = normalizeBasename(targetStr);
  const itemBase = normalizeBasename(name);
  if (targetBase && itemBase && (targetBase === itemBase || targetBase.includes(itemBase) || itemBase.includes(targetBase))) {
    return true;
  }

  if (path.includes(targetStr) || relPath.includes(targetStr)) return true;
  if (projName && (projName.includes(targetStr) || targetStr.includes(projName))) return true;
  if (hookTitle && targetStr.length > 5 && (hookTitle.includes(targetStr) || targetStr.includes(hookTitle))) return true;

  return false;
}
