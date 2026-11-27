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
    cyan: 'bg-[#131E33] text-[#60A5FA] border-[#233B66]',
    emerald: 'bg-[#10241D] text-[#34D399] border-[#1E4D3B]',
    rose: 'bg-[#271417] text-[#F87171] border-[#52232A]',
    amber: 'bg-[#241D11] text-[#FBBF24] border-[#4D3B19]',
    purple: 'bg-[#1B1D22] text-[#D4D4D8] border-[#2B2E36]',
    slate: 'bg-[#1B1D22] text-[#8E929B] border-[#23262D]'
  };

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-[11px]',
    md: 'px-2.5 py-1 text-xs'
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border font-semibold select-none ${
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
