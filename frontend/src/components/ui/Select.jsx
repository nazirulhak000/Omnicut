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
          className={`w-full py-2.5 pl-3.5 pr-9 rounded-xl bg-[#080B11] border border-white/[0.1] text-slate-100 text-base sm:text-sm font-medium focus:outline-none focus:border-[#25F4EE]/60 focus:ring-1 focus:ring-[#25F4EE]/40 transition-all shadow-inner appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
            error ? 'border-rose-500/60 focus:border-rose-500 focus:ring-rose-500/30' : ''
          } ${className}`}
          {...props}
        >
          {children ||
            options.map((opt) => (
              <option
                key={opt.value ?? opt.id ?? opt}
                value={opt.value ?? opt.id ?? opt}
                className="bg-[#0D111A] text-slate-200"
              >
                {opt.label ?? opt.name ?? opt}
              </option>
            ))}
        </select>
        <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
      </div>
      {error && (
        <p className="text-[11px] text-rose-400 font-medium">{error}</p>
      )}
    </div>
  );
});

export default Select;
