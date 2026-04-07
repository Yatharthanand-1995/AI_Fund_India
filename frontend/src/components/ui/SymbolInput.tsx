/**
 * SymbolInput - Validated stock symbol input with autocomplete
 * Ensures only valid NSE/BSE stock symbols are entered.
 */

import React, { useState, useRef, useEffect } from 'react';
import { Search } from 'lucide-react';
import { useStore } from '@/store/useStore';

const SYMBOL_REGEX = /^[A-Z0-9&-]{1,20}$/;

interface SymbolInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: (value: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  showIcon?: boolean;
}

export function SymbolInput({
  value,
  onChange,
  onSubmit,
  placeholder = 'Enter symbol (e.g., TCS, INFY)',
  className = '',
  disabled = false,
  showIcon = false,
}: SymbolInputProps) {
  const [validationError, setValidationError] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const { stockUniverse } = useStore();

  // Build flat symbol list from universe
  const allSymbols: string[] = React.useMemo(() => {
    if (!stockUniverse?.indices) return [];
    const set = new Set<string>();
    Object.values(stockUniverse.indices).forEach((syms: any) => {
      if (Array.isArray(syms)) syms.forEach((s: string) => set.add(s));
    });
    return Array.from(set).sort();
  }, [stockUniverse]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.toUpperCase();
    onChange(val);

    if (val && !SYMBOL_REGEX.test(val)) {
      setValidationError('Only letters, numbers, & and - allowed');
    } else {
      setValidationError('');
    }

    // Filter suggestions
    if (val.length >= 1 && allSymbols.length > 0) {
      const filtered = allSymbols
        .filter(s => s.startsWith(val) && s !== val)
        .slice(0, 8);
      setSuggestions(filtered);
      setShowSuggestions(filtered.length > 0);
    } else {
      setShowSuggestions(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && value && !validationError) {
      setShowSuggestions(false);
      onSubmit?.(value);
    }
    if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  const handleSelect = (symbol: string) => {
    onChange(symbol);
    setValidationError('');
    setShowSuggestions(false);
    onSubmit?.(symbol);
  };

  return (
    <div className="relative" ref={wrapperRef}>
      {showIcon && (
        <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
      )}
      <input
        type="text"
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onFocus={() => {
          if (suggestions.length > 0) setShowSuggestions(true);
        }}
        placeholder={placeholder}
        maxLength={20}
        disabled={disabled}
        className={`${className} ${validationError ? 'border-red-500 focus:ring-red-500 focus:border-red-500' : ''} ${showIcon ? 'pl-12' : ''}`}
        aria-invalid={!!validationError}
        aria-describedby={validationError ? 'symbol-error' : undefined}
        autoComplete="off"
      />
      {validationError && (
        <p id="symbol-error" className="absolute -bottom-5 left-0 text-xs text-red-600">
          {validationError}
        </p>
      )}
      {showSuggestions && (
        <ul className="absolute z-50 left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
          {suggestions.map(sym => (
            <li
              key={sym}
              onMouseDown={() => handleSelect(sym)}
              className="px-4 py-2 text-sm text-gray-800 hover:bg-blue-50 cursor-pointer font-mono"
            >
              {sym}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
