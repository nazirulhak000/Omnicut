// Product list fields (specs, selling points, pain points) edited as text,
// one item per line.
//
// Stored items are plain strings or labelled objects: the scraper and intake
// write { key, value } or { name, value } (some readers also accept { label,
// value }). The editor shows an object as "label: value" and writes it back
// in the shape it came in, so script generation keeps reading .value.

const LABEL_KEYS = ['key', 'name', 'label'];

const isObject = (item) => Boolean(item) && typeof item === 'object' && !Array.isArray(item);

/** One stored item as one line of text. */
export function listItemText(item) {
  if (item === null || item === undefined) return '';
  if (!isObject(item)) return String(item).trim();
  const labelKey = LABEL_KEYS.find((key) => typeof item[key] === 'string' && item[key].trim());
  const label = labelKey ? item[labelKey].trim() : '';
  const raw = item.value;
  const value = raw === null || raw === undefined
    ? ''
    : (typeof raw === 'object' ? JSON.stringify(raw) : String(raw).trim());
  if (label && value) return `${label}: ${value}`;
  return label || value || JSON.stringify(item);
}

/** A stored field (list, single string or single object) as editable text. */
export function listFieldText(field) {
  if (Array.isArray(field)) return field.map(listItemText).filter(Boolean).join('\n');
  return listItemText(field);
}

const lines = (text) => String(text || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean);

/** Number of items the text holds (non-empty lines). */
export const listLineCount = (text) => lines(text).length;

/**
 * Edited text back to the stored shape.
 *
 * Text that still reads the same as `original` returns `original` itself, so
 * opening and saving the form never rewrites a field nobody touched. When the
 * original held labelled objects, every line becomes one again, split at its
 * first colon, with the label key the original used.
 */
export function listFieldFromText(text, original) {
  const edited = lines(text);
  if (edited.join('\n') === lines(listFieldText(original)).join('\n') && Array.isArray(original)) {
    return original;
  }
  const sample = Array.isArray(original) ? original.find(isObject) : (isObject(original) ? original : null);
  if (!sample) return edited;
  const labelKey = LABEL_KEYS.find((key) => key in sample) || 'key';
  return edited.map((line) => {
    const at = line.indexOf(':');
    if (at <= 0) return { [labelKey]: '', value: line };
    return { [labelKey]: line.slice(0, at).trim(), value: line.slice(at + 1).trim() };
  });
}
