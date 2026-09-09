export function updateItemById(items = [], id, patch = {}) {
  return items.map((item) => (item?.id === id ? { ...item, ...patch } : item));
}

export function removeItemById(items = [], id) {
  return items.filter((item) => item?.id !== id);
}
