/**
 * SymbolInput - Validated stock symbol input component
 * Ensures only valid NSE/BSE stock symbols are entered.
 */

import React, { useState } from 'react';
import { Search } from 'lucide-react';

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

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.toUpperCase();
    onChange(val);

    if (val && !SYMBOL_REGEX.test(val)) {
      setValidationError('Only letters, numbers, & and - allowed');
    } else {
      setValidationError('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && value && !validationError) {
      onSubmit?.(value);
    }
  };

  return (
    <div className="relative">
      {showIcon && (
        <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
      )}
      <input
        type="text"
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        maxLength={20}
        disabled={disabled}
        className={`${className} ${validationError ? 'border-red-500 focus:ring-red-500 focus:border-red-500' : ''} ${showIcon ? 'pl-12' : ''}`}
        aria-invalid={!!validationError}
        aria-describedby={validationError ? 'symbol-error' : undefined}
      />
      {validationError && (
        <p id="symbol-error" className="absolute -bottom-5 left-0 text-xs text-red-600">
          {validationError}
        </p>
      )}
    </div>
  );
}
