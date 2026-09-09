export function createLatestSaveQueue(save, callbacks = {}) {
  let pending = null;
  let active = null;
  let activeJob = null;
  let sequence = 0;
  let invalidationGeneration = 0;

  const enqueue = (projectName, payload) => {
    const job = {
      projectName,
      payload,
      sequence: ++sequence,
      invalidationGeneration,
    };
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
        activeJob = job;
        callbacks.onSaving?.(job);
        try {
          await save(job.projectName, job.payload);
        } catch (error) {
          // A baseline/project switch may intentionally discard all pending
          // work while this request is in flight. Do not resurrect that stale
          // job when its request fails after the discard.
          if (
            invalidationGeneration === job.invalidationGeneration
            && (!pending || pending.sequence < job.sequence)
          ) pending = job;
          callbacks.onError?.(job, error);
          throw error;
        }
        lastSaved = job;
        callbacks.onSaved?.(job, job.sequence === sequence);
      }
      return lastSaved;
    })();

    try {
      return await active;
    } finally {
      active = null;
      activeJob = null;
    }
  };

  return {
    enqueue,
    flush,
    clearPending() {
      pending = null;
      invalidationGeneration += 1;
    },
    peekPending() {
      return pending;
    },
    peekActive() {
      return activeJob;
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
