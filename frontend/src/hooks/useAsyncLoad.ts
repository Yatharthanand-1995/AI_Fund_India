/**
 * useAsyncLoad - Generic hook for async data loading with consistent error handling
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useStore } from '@/store/useStore';

interface UseAsyncLoadOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
  showToast?: boolean;
}

interface UseAsyncLoadResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  retry: () => void;
  setData: React.Dispatch<React.SetStateAction<T | null>>;
}

export function useAsyncLoad<T>(
  asyncFn: () => Promise<T>,
  deps: React.DependencyList = [],
  options: UseAsyncLoadOptions<T> = {}
): UseAsyncLoadResult<T> {
  const { onSuccess, onError, enabled = true, showToast = true } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const addToast = useStore(state => state.addToast);

  // Use refs to avoid stale closure issues with callbacks
  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);
  onSuccessRef.current = onSuccess;
  onErrorRef.current = onError;

  const load = useCallback(async () => {
    if (!enabled) return;

    setLoading(true);
    setError(null);

    try {
      const result = await asyncFn();
      setData(result);
      onSuccessRef.current?.(result);
    } catch (err) {
      const loadError = err instanceof Error ? err : new Error(String(err));
      setError(loadError);
      onErrorRef.current?.(loadError);

      if (showToast) {
        addToast({
          type: 'error',
          message: loadError.message || 'An error occurred',
        });
      }
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, showToast, ...deps]);

  useEffect(() => {
    load();
  }, [load]);

  return { data, loading, error, retry: load, setData };
}
