export function createChannelDraftParticipant(initialValue) {
  let baseline = structuredClone(initialValue);
  let current = initialValue;
  let handlers = {};
  let active = null;
  const key = value => JSON.stringify(value);
  const run = action => {
    if (active) return active;
    active = Promise.resolve().then(action).finally(() => { active = null; });
    return active;
  };
  return {
    observe(value, nextHandlers) { current = value; handlers = nextHandlers; },
    isDirty: () => !!active || key(current) !== key(baseline),
    isSaving: () => !!active,
    markSaved(value) { baseline = structuredClone(value); },
    acceptExternal(value) {
      if (active || key(current) !== key(baseline) || key(current) === key(value)) return false;
      baseline = structuredClone(value);
      current = value;
      return true;
    },
    run,
    save({ forSwitch = false } = {}) {
      if (active) return active;
      const savedValue = structuredClone(current);
      const save = forSwitch ? (handlers.saveForSwitch || handlers.save) : handlers.save;
      return run(async () => {
        const result = await save(savedValue);
        baseline = savedValue;
        return result;
      });
    },
    async discard() {
      if (active) await active.catch(() => {});
      const restored = structuredClone(baseline);
      handlers.reset(restored);
      current = restored;
    },
  };
}
