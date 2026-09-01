import React from 'react';

export function Badge({
  children,
  variant = 'purple', // 'purple' | 'cyan' | 'emerald' | 'rose' | 'amber' | 'slate'
  size = 'md', // 'sm' | 'md'
  icon: Icon,
  className = '',
  ...props
}) {
  const variantStyles = {
    purple: 'bg-[#7C3AED]/15 text-[#C4B5FD] border-[#7C3AED]/30',
    cyan: 'bg-sky-500/10 text-sky-300 border-sky-500/25',
    emerald: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/25',
    rose: 'bg-rose-500/10 text-rose-300 border-rose-500/25',
    amber: 'bg-amber-500/10 text-amber-300 border-amber-500/25',
    slate: 'bg-white/[0.04] text-slate-300 border-white/[0.07]'
  };

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-[10px]',
    md: 'px-2.5 py-1 text-xs'
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold font-mono select-none ${
        sizeStyles[size] || sizeStyles.md
      } ${variantStyles[variant] || variantStyles.purple} ${className}`}
      {...props}
    >
      {Icon && <Icon className="w-3 h-3 flex-shrink-0" />}
      <span>{children}</span>
    </span>
  );
}

export default Badge;
