import React, { forwardRef } from 'react';

export const Input = forwardRef(function Input(
  {
    label,
    error,
    helperText,
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
      <input
        ref={ref}
        disabled={disabled}
        className={`w-full py-2 px-3 rounded-lg bg-[#1B1D22] border border-[#2B2E36] text-[#F4F4F5] text-base sm:text-sm placeholder-[#5C6069] focus:outline-none focus:border-[#3A3E4A] focus:ring-1 focus:ring-[#3A3E4A] transition-[border-color,box-shadow,background-color] duration-150 ease-out disabled:opacity-50 disabled:cursor-not-allowed ${
          error ? 'border-[#52232A] focus:border-[#F87171] focus:ring-[#F87171]/30' : ''
        } ${className}`}
        {...props}
      />
      {error && (
        <p className="text-sm text-rose-400 font-medium">{error}</p>
      )}
      {helperText && !error && (
        <p className="text-sm text-slate-500">{helperText}</p>
      )}
    </div>
  );
});

export const Textarea = forwardRef(function Textarea(
  {
    label,
    error,
    helperText,
    className = '',
    containerClassName = '',
    disabled = false,
    rows = 3,
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
      <textarea
        ref={ref}
        rows={rows}
        disabled={disabled}
        className={`w-full py-2 px-3 rounded-lg bg-[#1B1D22] border border-[#2B2E36] text-[#F4F4F5] text-base sm:text-sm placeholder-[#5C6069] focus:outline-none focus:border-[#3A3E4A] focus:ring-1 focus:ring-[#3A3E4A] transition-[border-color,box-shadow,background-color] duration-150 ease-out resize-y disabled:opacity-50 disabled:cursor-not-allowed ${
          error ? 'border-[#52232A] focus:border-[#F87171] focus:ring-[#F87171]/30' : ''
        } ${className}`}
        {...props}
      />
      {error && (
        <p className="text-sm text-rose-400 font-medium">{error}</p>
      )}
      {helperText && !error && (
        <p className="text-sm text-slate-500">{helperText}</p>
      )}
    </div>
  );
});

export default Input;
