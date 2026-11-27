import React, { forwardRef } from 'react';
import { ChevronDown } from 'lucide-react';

export const Select = forwardRef(function Select(
  {
    label,
    error,
    options = [],
    children,
    className = '',
    containerClassName = '',
    disabled = false,
    ...props
  },
  ref
) {
  return (
    <div className={`space-y-1.5 ${containerClassName}`}>
      {label && (
        <label className="block text-xs font-semibold text-slate-300">
          {label}
        </label>
      )}
      <div className="relative">
        <select
          ref={ref}
          disabled={disabled}
          className={`w-full py-2 pl-3 pr-9 rounded-lg bg-[#1B1D22] border border-[#2B2E36] text-[#F4F4F5] text-base sm:text-sm font-medium focus:outline-none focus:border-[#3A3E4A] focus:ring-1 focus:ring-[#3A3E4A] transition-[border-color,box-shadow,background-color] duration-150 ease-out appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
            error ? 'border-[#52232A] focus:border-[#F87171] focus:ring-[#F87171]/30' : ''
          } ${className}`}
          {...props}
        >
          {children ||
            options.map((opt) => (
              <option
                key={opt.value ?? opt.id ?? opt}
                value={opt.value ?? opt.id ?? opt}
                className="bg-[#14161A] text-[#F4F4F5]"
              >
                {opt.label ?? opt.name ?? opt}
              </option>
            ))}
        </select>
        <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
      </div>
      {error && (
        <p className="text-sm text-rose-400 font-medium">{error}</p>
      )}
    </div>
  );
});

export default Select;
