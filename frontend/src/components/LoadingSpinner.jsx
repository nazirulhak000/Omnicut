import React from 'react';
import { Loader2 } from 'lucide-react';

export default function LoadingSpinner({ message = 'กำลังโหลดโมดูล...' }) {
  return (
    <div className="w-full min-h-[400px] flex flex-col items-center justify-center p-8 space-y-4 animate-fadeIn select-none">
      <div className="relative flex items-center justify-center">
        {/* Glowing Background Pulse */}
        <div className="absolute w-16 h-16 rounded-full bg-gradient-to-tr from-[#FE2C55]/30 to-[#25F4EE]/30 blur-xl animate-pulse" />
        
        {/* Glass Card Container */}
        <div className="w-14 h-14 rounded-2xl glass-card border border-[#25F4EE]/30 flex items-center justify-center shadow-lg shadow-[#25F4EE]/10 relative z-10">
          <Loader2 className="w-7 h-7 text-[#25F4EE] animate-spin" />
        </div>
      </div>

      <div className="text-center space-y-1 z-10">
        <p className="text-xs sm:text-sm font-bold text-white font-kanit tracking-wide">
          {message}
        </p>
        <p className="text-sm text-slate-500 font-mono">
          Dynamic Module Code-Splitting Active
        </p>
      </div>
    </div>
  );
}
