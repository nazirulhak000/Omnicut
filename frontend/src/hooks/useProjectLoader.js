import { useCallback, useEffect, useRef, useState } from 'react';


export function useProjectLoader({ fetchProject, beforeLoad, mapProject, onStart, onLoaded }) {
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const requestSequence = useRef(0);
  const callbacks = useRef({ fetchProject, beforeLoad, mapProject, onStart, onLoaded });
  callbacks.current = { fetchProject, beforeLoad, mapProject, onStart, onLoaded };

  useEffect(() => () => {
    requestSequence.current += 1;
  }, []);

  const loadProject = useCallback(async (name) => {
    if (!name) return null;
    const sequence = ++requestSequence.current;
    setLoading(true);
    setLoadError(null);
    try {
      await callbacks.current.beforeLoad?.(name);
      if (sequence !== requestSequence.current) return null;
      callbacks.current.onStart?.(name);
      const manifest = await callbacks.current.fetchProject(name);
      if (sequence !== requestSequence.current) return null;
      const mapped = callbacks.current.mapProject
        ? callbacks.current.mapProject(manifest)
        : manifest;
      callbacks.current.onLoaded?.(name, mapped, manifest);
      return mapped;
    } catch (error) {
      if (sequence === requestSequence.current) {
        setLoadError(error?.friendlyMessage || error?.message || `โหลดโปรเจกต์ ${name} ไม่สำเร็จ`);
      }
      return null;
    } finally {
      if (sequence === requestSequence.current) setLoading(false);
    }
  }, []);

  return { loadProject, loading, loadError, setLoadError };
}
