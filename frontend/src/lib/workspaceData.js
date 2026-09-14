/**
 * Coordinates data shared by the application shell. A resource has one
 * in-flight request and a short-lived value, so navigation cannot create a
 * burst of identical reads while a render is also updating the workspace.
 */
export function createWorkspaceDataCoordinator(loaders, now = () => Date.now()) {
  const entries = new Map();

  const load = (key, loader, { maxAgeMs = 0, force = false } = {}) => {
    const current = entries.get(key);
    const fresh = current?.value !== undefined && now() - current.savedAt <= maxAgeMs;
    if (!force && fresh) return Promise.resolve(current.value);
    if (!force && current?.pending) return current.pending;

    const pending = Promise.resolve()
      .then(loader)
      .then((value) => {
        entries.set(key, { value, savedAt: now(), pending: null });
        return value;
      })
      .catch((error) => {
        // A failed request must not poison the next retry.
        if (entries.get(key)?.pending === pending) entries.delete(key);
        throw error;
      });
    entries.set(key, { value: current?.value, savedAt: current?.savedAt || 0, pending });
    return pending;
  };

  return {
    loadShell({ force = false } = {}) {
      return Promise.all([
        load('status', loaders.getSystemStatus, { maxAgeMs: 2_000, force }),
        load('rawVideos', loaders.getRawVideos, { maxAgeMs: 2_000, force }),
      ]).then(([status, videos]) => ({ status, videos }));
    },
    loadExports({ force = false } = {}) {
      return load('exports', loaders.getExports, { maxAgeMs: 2_000, force });
    },
    invalidate(...keys) {
      keys.forEach((key) => entries.delete(key));
    },
  };
}
