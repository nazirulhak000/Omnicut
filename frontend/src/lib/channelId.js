/** P1 channel slug contract. Never trim or lowercase an explicitly supplied ID. */
export function isValidChannelId(value) {
  return typeof value === 'string'
    && /^[a-z][a-z0-9_-]{1,31}$/.test(value)
    && !/[\r\n]/.test(value);
}

/** Returns the original valid ID, or a machine-readable validation error. */
export function assertChannelId(value) {
  if (!isValidChannelId(value)) {
    const error = new TypeError('channel_id ต้องเป็น slug ตัวพิมพ์เล็ก 2–32 ตัวอักษร');
    error.code = 'channel_scope_invalid';
    throw error;
  }
  return value;
}
