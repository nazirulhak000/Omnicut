export function createLatestSaveQueue(save, callbacks = {}) {
  let pending = null;
  let active = null;
  let sequence = 0;

  const enqueue = (projectName, payload) => {
    const job = { projectName, payload, sequence: ++sequence };
    pending = job;
    callbacks.onQueued?.(job);
    return job;
  };

  const flush = async () => {
    if (active) return active;
    if (!pending) return null;

    active = (async () => {
      let lastSaved = null;
      while (pending) {
        const job = pending;
        pending = null;
        callbacks.onSaving?.(job);
        try {
          await save(job.projectName, job.payload);
        } catch (error) {
          if (!pending || pending.sequence < job.sequence) pending = job;
          callbacks.onError?.(job, error);
          throw error;
        }
        lastSaved = job;
        callbacks.onSaved?.(job);
      }
      return lastSaved;
    })();

    try {
      return await active;
    } finally {
      active = null;
    }
  };

  return {
    enqueue,
    flush,
    clearPending() {
      pending = null;
    },
    peekPending() {
      return pending;
    },
    hasPending() {
      return !!pending;
    },
    isSaving() {
      return !!active;
    },
    latestSequence() {
      return sequence;
    },
  };
}
