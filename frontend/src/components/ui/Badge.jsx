import React from 'react';

export function Badge({
  children,
  variant = 'cyan', // 'cyan' | 'emerald' | 'rose' | 'amber' | 'purple' | 'slate'
  size = 'md', // 'sm' | 'md'
  icon: Icon,
  className = '',
  ...props
}) {
  const variantStyles = {
    cyan: 'bg-[#25F4EE]/10 text-[#25F4EE] border-[#25F4EE]/30',
    emerald: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    rose: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
    amber: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    purple: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
    slate: 'bg-white/[0.05] text-slate-300 border-white/[0.08]'
  };

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-sm',
    md: 'px-2.5 py-1 text-xs'
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-bold select-none ${
        sizeStyles[size] || sizeStyles.md
      } ${variantStyles[variant] || variantStyles.cyan} ${className}`}
      {...props}
    >
      {Icon && <Icon className="w-3 h-3 flex-shrink-0" />}
      <span>{children}</span>
    </span>
  );
}

export default Badge;
