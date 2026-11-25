import React from 'react';

export default function ToggleControl({
  label,
  checked,
  onChange,
  icon: Icon,
  activeText,
  inactiveText,
  activeClass = 'bg-[#25F4EE]/15 border-[#25F4EE] text-[#25F4EE]',
  inactiveClass = 'bg-white/[0.04] border-white/[0.08] text-slate-400 hover:text-white',
}) {
  const displayText = checked
    ? (activeText || label)
    : (inactiveText || label);

  return (
    <button
      type="button"
      onClick={() => onChange?.(!checked)}
      className={`w-full py-2 px-3 rounded-xl border text-xs font-semibold flex items-center justify-between cursor-pointer active:scale-[0.98] transition-[background-color,border-color,color,transform] duration-150 active:duration-100 ease-out ${
        checked ? activeClass : inactiveClass
      }`}
    >
      <span className="flex items-center gap-2">
        {Icon && <Icon className="w-3.5 h-3.5" />}
        <span>{displayText}</span>
      </span>
      <div
        className={`w-8 h-4 rounded-full p-0.5 transition-colors duration-150 ease-out ${
          checked ? 'bg-[#25F4EE]' : 'bg-[#363430]'
        }`}
      >
        <div
          className={`w-3 h-3 rounded-full bg-black transition-transform duration-150 ease-out ${
            checked ? 'translate-x-4' : 'translate-x-0'
          }`}
        />
      </div>
    </button>
  );
}
