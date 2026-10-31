import React, { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

export const Button = forwardRef(function Button(
  {
    children,
    variant = 'primary',
    size = 'md',
    loading = false,
    disabled = false,
    icon: Icon,
    iconRight: IconRight,
    className = '',
    ...props
  },
  ref
) {
  const baseStyles = 'inline-flex items-center justify-center font-bold transition-all cursor-pointer select-none active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100';

  // Touch targets: on phones (<768px) and any coarse pointer every size is at
  // least 44x44 with 14px text; desktop mouse layouts keep their density.
  const touchTarget = 'max-md:min-h-11 pointer-coarse:min-h-11';
  const sizeStyles = {
    sm: `px-2.5 py-1.5 rounded-lg text-xs max-md:text-sm gap-1.5 ${touchTarget}`,
    md: `px-4 py-2.5 rounded-xl text-xs sm:text-sm max-md:text-sm gap-2 ${touchTarget}`,
    lg: 'px-5 py-3.5 rounded-2xl text-sm sm:text-base gap-2.5 min-h-12',
    icon: `p-2 rounded-xl text-xs sm:text-sm max-md:text-sm ${touchTarget} max-md:min-w-11 pointer-coarse:min-w-11`
  };

  const variantStyles = {
    primary: 'bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] text-white hover:opacity-95 shadow-md shadow-[#FE2C55]/20',
    neon: 'bg-[#25F4EE] hover:brightness-110 text-slate-950 shadow-lg shadow-[#25F4EE]/30',
    tiktok: 'bg-gradient-to-r from-[#FE2C55] to-[#FF0050] hover:brightness-110 text-white shadow-lg shadow-[#FE2C55]/25',
    secondary: 'bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-slate-200 hover:text-white',
    danger: 'bg-rose-600 hover:bg-rose-700 text-white shadow-md shadow-rose-600/20',
    ghost: 'bg-transparent hover:bg-white/[0.05] text-slate-400 hover:text-white',
    outline: 'bg-transparent border border-[#25F4EE]/40 text-[#25F4EE] hover:bg-[#25F4EE]/10'
  };

  return (
    <button
      ref={ref}
      data-oc-button={Object.hasOwn(variantStyles, variant) ? variant : 'primary'}
      disabled={disabled || loading}
      className={`${baseStyles} ${sizeStyles[size] || sizeStyles.md} ${variantStyles[variant] || variantStyles.primary} ${className}`}
      {...props}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />
      ) : Icon ? (
        <Icon className="w-4 h-4 flex-shrink-0" />
      ) : null}
      {children}
      {!loading && IconRight && (
        <IconRight className="w-4 h-4 flex-shrink-0" />
      )}
    </button>
  );
});

export default Button;
