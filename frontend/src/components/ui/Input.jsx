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
        className={`w-full py-2.5 px-3.5 rounded-xl bg-[#080B11] border border-white/[0.1] text-slate-100 text-base sm:text-sm placeholder-slate-600 focus:outline-none focus:border-[#25F4EE]/60 focus:ring-1 focus:ring-[#25F4EE]/40 transition-all shadow-inner disabled:opacity-50 disabled:cursor-not-allowed ${
          error ? 'border-rose-500/60 focus:border-rose-500 focus:ring-rose-500/30' : ''
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
        className={`w-full py-2.5 px-3.5 rounded-xl bg-[#080B11] border border-white/[0.1] text-slate-100 text-base sm:text-sm placeholder-slate-600 focus:outline-none focus:border-[#25F4EE]/60 focus:ring-1 focus:ring-[#25F4EE]/40 transition-all shadow-inner resize-y disabled:opacity-50 disabled:cursor-not-allowed ${
          error ? 'border-rose-500/60 focus:border-rose-500 focus:ring-rose-500/30' : ''
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
