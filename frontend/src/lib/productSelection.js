export function resolveSelectedProduct(products, requestedId) {
  if (!Array.isArray(products) || products.length === 0) return null;
  if (requestedId) return products.find((product) => product?.id === requestedId) || null;
  return products[0] || null;
}

export function resolveHistoryTargetId(externalId, previousExternalId, localId) {
  if (externalId && externalId !== previousExternalId) return externalId;
  return localId || null;
}
