/**
 * useUrlFilters hook
 *
 * Syncs a filters object to/from URL search params so filter state
 * survives page reload and can be shared via link.
 *
 * Supports: string, number, string[] param types.
 * Arrays are stored as comma-separated values: ?sectors=IT,Finance
 */

import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';

type FilterValue = string | number | string[] | undefined;
type Filters = Record<string, FilterValue>;

/**
 * Serialise a filters object to URLSearchParams.
 * Undefined / empty values are omitted to keep URLs clean.
 */
function filtersToParams(filters: Filters): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === '') continue;
    if (Array.isArray(value)) {
      if (value.length > 0) params.set(key, value.join(','));
    } else {
      params.set(key, String(value));
    }
  }
  return params;
}

/**
 * Parse URLSearchParams back into a Filters object.
 * arrayKeys: keys that should be treated as string arrays.
 * numberKeys: keys that should be parsed as numbers.
 */
function paramsToFilters<T extends object>(
  params: URLSearchParams,
  arrayKeys: string[],
  numberKeys: string[]
): Partial<T> {
  const result: Filters = {};
  params.forEach((value, key) => {
    if (arrayKeys.includes(key)) {
      result[key] = value.split(',').filter(Boolean);
    } else if (numberKeys.includes(key)) {
      const num = parseFloat(value);
      if (!isNaN(num)) result[key] = num;
    } else {
      result[key] = value;
    }
  });
  return result as Partial<T>;
}

interface UseUrlFiltersOptions {
  /** Keys that are string arrays (comma-separated in URL) */
  arrayKeys?: string[];
  /** Keys that should be parsed as numbers */
  numberKeys?: string[];
  /** Replace history instead of push (avoids back-button filter history) */
  replace?: boolean;
}

export function useUrlFilters<T extends object>(
  options: UseUrlFiltersOptions = {}
): [Partial<T>, (filters: T) => void, () => void] {
  const { arrayKeys = [], numberKeys = [], replace = true } = options;
  const [searchParams, setSearchParams] = useSearchParams();

  // Read current filters from URL
  const filters = paramsToFilters<T>(searchParams, arrayKeys, numberKeys);

  // Write filters to URL
  const setFilters = useCallback(
    (newFilters: T) => {
      const params = filtersToParams(newFilters as Filters);
      setSearchParams(params, { replace });
    },
    [setSearchParams, replace]
  );

  // Clear all filters
  const clearFilters = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace });
  }, [setSearchParams, replace]);

  return [filters, setFilters, clearFilters];
}
