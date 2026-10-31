/** UI-only theme activation. The production default stays on the legacy renderer. */
export function isUiThemeV2Enabled(value) {
  return value === 'true';
}

/** Use exact migrated legacy values without rewriting any legacy storage key. */
export function applyLegacyUiTheme(target, preferences, enabled = false) {
  if (!enabled || !target) return () => {};
  const config = preferences.legacyGlassConfig;
  const previousTheme = target.getAttribute('data-theme');
  const values = {
    '--glass-opacity': (config.opacity / 100).toFixed(2),
    '--glass-blur': `${config.blur}px`,
    '--glare-opacity': (config.glare / 100).toFixed(2),
    '--orbs-opacity': (config.orbsGlow / 100).toFixed(2),
    '--glass-saturate': `${config.saturate}%`,
  };
  const previous = Object.keys(values).map((name) => [name, target.style.getPropertyValue(name), target.style.getPropertyPriority(name)]);
  target.setAttribute('data-theme', preferences.activePresetId);
  for (const [name, value] of Object.entries(values)) target.style.setProperty(name, value);
  return () => {
    if (previousTheme === null) target.removeAttribute('data-theme');
    else target.setAttribute('data-theme', previousTheme);
    for (const [name, value, priority] of previous) {
      if (value) target.style.setProperty(name, value, priority);
      else target.style.removeProperty(name);
    }
  };
}

/**
 * Apply only the UI namespace and return a precise rollback for StrictMode,
 * preset changes, and unmount. Never touches video styles or legacy preferences.
 */
export function applyResolvedUiTheme(target, resolved, enabled = false) {
  if (!enabled || !target || !resolved || resolved.isLegacy) return () => {};
  const attributes = {
    'data-ui-theme': 'balanced',
    'data-ui-effects': resolved.effects,
  };
  const previousAttributes = Object.fromEntries(
    Object.keys(attributes).map((name) => [name, target.getAttribute(name)]),
  );
  const previousVariables = [];
  for (const [name, value] of Object.entries(resolved.variables || {})) {
    if (!name.startsWith('--oc-ui-')) continue;
    previousVariables.push([name, target.style.getPropertyValue(name), target.style.getPropertyPriority(name)]);
    target.style.setProperty(name, String(value));
  }
  for (const [name, value] of Object.entries(attributes)) target.setAttribute(name, value);
  return () => {
    for (const [name, value] of Object.entries(previousAttributes)) {
      if (value === null) target.removeAttribute(name);
      else target.setAttribute(name, value);
    }
    for (const [name, value, priority] of previousVariables) {
      if (value) target.style.setProperty(name, value, priority);
      else target.style.removeProperty(name);
    }
  };
}
