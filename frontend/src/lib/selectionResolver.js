export function resolveSelectedItem(selection, types, items = [], {
  fallback = null,
  matches = (item, id) => item?.id === id,
} = {}) {
  const acceptedTypes = Array.isArray(types) ? types : [types];
  if (!selection || !acceptedTypes.includes(selection.type)) return null;
  return items.find((item) => matches(item, selection.id)) || fallback;
}
