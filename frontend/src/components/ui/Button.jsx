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
  const baseStyles = 'inline-flex items-center justify-center font-bold motion-press active:duration-100 cursor-pointer select-none active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100';

  // Touch targets: on phones (<768px) and any coarse pointer every size is at
  // least 44x44 with 14px text; desktop mouse layouts keep their density.
  const touchTarget = 'max-md:min-h-11 pointer-coarse:min-h-11';
  const sizeStyles = {
    sm: `px-2.5 py-1.5 rounded-lg text-xs max-md:text-sm gap-1.5 ${touchTarget}`,
    md: `px-3.5 py-2 rounded-lg text-xs sm:text-sm max-md:text-sm gap-2 ${touchTarget}`,
    lg: 'px-5 py-3 rounded-xl text-sm sm:text-base gap-2.5 min-h-12',
    icon: `p-2 rounded-lg text-xs sm:text-sm max-md:text-sm ${touchTarget} max-md:min-w-11 pointer-coarse:min-w-11`
  };

  const variantStyles = {
    primary: 'bg-[#F4F4F5] text-[#0B0C0E] font-semibold hover:bg-[#E4E4E7]',
    neon: 'bg-[#F4F4F5] hover:bg-[#E4E4E7] text-[#0B0C0E] font-semibold',
    tiktok: 'bg-[#F4F4F5] hover:bg-[#E4E4E7] text-[#0B0C0E] font-semibold',
    secondary: 'bg-[#1B1D22] hover:bg-[#22252C] border border-[#2B2E36] hover:border-[#3A3E4A] text-[#F4F4F5]',
    danger: 'bg-[#271417] hover:bg-[#3A1B20] border border-[#52232A] text-[#F87171]',
    ghost: 'bg-transparent hover:bg-[#1B1D22] text-[#8E929B] hover:text-[#F4F4F5]',
    outline: 'bg-transparent border border-[#2B2E36] text-[#F4F4F5] hover:bg-[#1B1D22] hover:border-[#3A3E4A]'
  };

  return (
    <button
      ref={ref}
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
