import { useState, useEffect } from 'react';

/**
 * useDebounce Hook
 * Delays updating the value until a specified timeout has elapsed without further changes.
 * Ideal for search query inputs, real-time filtering, and auto-saving forms.
 */
export function useDebounce(value, delay = 300) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

export default useDebounce;
